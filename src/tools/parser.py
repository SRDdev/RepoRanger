import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict


class ImportType(Enum):
    """Types of imports found in Python code."""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    WILDCARD = "wildcard"
    ALIASED = "aliased"
    CONDITIONAL = "conditional"


@dataclass
class ImportStatement:
    """Detailed representation of an import statement."""
    module: Optional[str]
    names: List[str]
    aliases: Dict[str, str] = field(default_factory=dict)
    level: int = 0
    import_type: ImportType = ImportType.ABSOLUTE
    line_number: int = 0
    col_offset: int = 0
    raw_statement: str = ""
    is_future_import: bool = False
    parent_node_type: Optional[str] = None  # For conditional imports


@dataclass
class FunctionInfo:
    """Information about a function definition."""
    name: str
    line_number: int
    args: List[str]
    decorators: List[str]
    is_async: bool = False
    is_method: bool = False
    docstring: Optional[str] = None
    complexity: int = 0
    calls: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class definition."""
    name: str
    line_number: int
    bases: List[str]
    decorators: List[str]
    methods: List[str]
    docstring: Optional[str] = None
    is_dataclass: bool = False
    attributes: List[str] = field(default_factory=list)


@dataclass
class CodeMetrics:
    """Comprehensive code quality and complexity metrics."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    docstring_lines: int = 0
    function_count: int = 0
    class_count: int = 0
    method_count: int = 0
    import_count: int = 0
    cyclomatic_complexity: int = 0
    max_nesting_depth: int = 0
    avg_function_length: float = 0.0


@dataclass
class FileAnalysis:
    """Complete analysis of a single Python file."""
    file_path: str
    module_name: Optional[str] = None
    imports: List[ImportStatement] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    global_variables: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    metrics: CodeMetrics = field(default_factory=CodeMetrics)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ast_tree: Optional[ast.AST] = None
    encoding: str = "utf-8"
    has_main_block: bool = False
    shebang: Optional[str] = None


class PythonCodeParser:
    """
    A comprehensive Python code parser with advanced dependency resolution,
    metrics calculation, AST analysis, and error handling.
    
    Features:
    - Complete AST-based parsing
    - Relative and absolute import resolution
    - Cyclomatic complexity calculation
    - Function and class extraction with metadata
    - Dependency graph generation (forward and reverse)
    - Circular dependency detection
    - Dead code detection
    - Module usage analysis
    """
    
    def __init__(self, 
                 repo_root: str,
                 ignore_patterns: Optional[List[str]] = None,
                 max_file_size: int = 10_000_000,
                 strict_mode: bool = False):
        """
        Initialize the parser.
        
        Args:
            repo_root: Root directory of the Python codebase
            ignore_patterns: Patterns to ignore (e.g., ['__pycache__', 'venv'])
            max_file_size: Maximum file size to parse (in bytes)
            strict_mode: If True, treat warnings as errors
        """
        self.repo_root = Path(repo_root).resolve()
        self.ignore_patterns = ignore_patterns or [
            '__pycache__', '.git', 'venv', 'env', '.venv',
            'dist', 'build', '.pytest_cache', 'coverage',
            '.tox', '.eggs', '*.egg-info'
        ]
        self.max_file_size = max_file_size
        self.strict_mode = strict_mode
        
        # Core data structures
        self.module_map: Dict[str, str] = {}  # module_name -> file_path
        self.file_analyses: Dict[str, FileAnalysis] = {}  # file_path -> analysis
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.package_map: Dict[str, List[str]] = defaultdict(list)  # package -> modules
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'parsed_files': 0,
            'failed_files': 0,
            'total_imports': 0,
            'total_functions': 0,
            'total_classes': 0,
        }
        
        # Index the repository
        self._index_repository()

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path)
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False

    def _index_repository(self) -> None:
        """
        Index all Python files in the repository.
        Builds comprehensive module maps for import resolution.
        """
        print(f"Indexing repository: {self.repo_root}")
        
        for root, dirs, files in os.walk(self.repo_root):
            # Filter ignored directories in-place
            dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                abs_path = Path(root) / file
                
                if self._should_ignore(abs_path):
                    continue
                
                # Check file size
                try:
                    if abs_path.stat().st_size > self.max_file_size:
                        print(f"Skipping large file: {abs_path}")
                        continue
                except OSError as e:
                    print(f"Error accessing {abs_path}: {e}")
                    continue
                
                self.stats['total_files'] += 1
                
                # Convert to module notation
                module_name = self._path_to_module(abs_path)
                if module_name:
                    self.module_map[module_name] = str(abs_path)
                    
                    # Track package hierarchy
                    parts = module_name.split('.')
                    for i in range(len(parts)):
                        package = '.'.join(parts[:i+1])
                        if package not in self.package_map:
                            self.package_map[package] = []
        
        print(f"Indexed {self.stats['total_files']} Python files")
        print(f"Created {len(self.module_map)} module mappings")

    def _path_to_module(self, path: Path) -> Optional[str]:
        """Convert file path to Python module notation."""
        try:
            rel_path = path.relative_to(self.repo_root)
            parts = list(rel_path.parts)
            
            # Remove .py extension
            parts[-1] = parts[-1].replace('.py', '')
            
            # Handle __init__.py files
            if parts[-1] == '__init__':
                parts.pop()
            
            if not parts:
                return None
                
            return '.'.join(parts)
        except (ValueError, IndexError):
            return None

    def _module_to_path(self, module_name: str) -> Optional[str]:
        """Convert module name to file path."""
        # Direct lookup
        if module_name in self.module_map:
            return self.module_map[module_name]
        
        # Try as package (__init__.py)
        init_module = f"{module_name}.__init__"
        if init_module in self.module_map:
            return self.module_map[init_module]
        
        return None

    def analyze_file(self, file_path: str) -> FileAnalysis:
        """
        Perform comprehensive analysis on a single Python file.
        
        Args:
            file_path: Path to file (relative to repo_root or absolute)
            
        Returns:
            FileAnalysis object with complete information
        """
        # Normalize path
        if Path(file_path).is_absolute():
            abs_path = Path(file_path)
        else:
            abs_path = (self.repo_root / file_path).resolve()
        
        # Get relative path for storage
        try:
            rel_path = str(abs_path.relative_to(self.repo_root))
        except ValueError:
            rel_path = str(abs_path)
        
        analysis = FileAnalysis(file_path=rel_path)
        
        if not abs_path.exists():
            analysis.errors.append(f"File not found: {abs_path}")
            self.stats['failed_files'] += 1
            return analysis
        
        # Get module name
        analysis.module_name = self._path_to_module(abs_path)
        
        try:
            # Read file content
            with open(abs_path, 'rb') as f:
                raw_content = f.read()
            
            # Detect encoding
            try:
                content = raw_content.decode('utf-8')
                analysis.encoding = 'utf-8'
            except UnicodeDecodeError:
                content = raw_content.decode('latin-1')
                analysis.encoding = 'latin-1'
                analysis.warnings.append("File uses non-UTF-8 encoding")
            
            # Check for shebang
            lines = content.split('\n')
            if lines and lines[0].startswith('#!'):
                analysis.shebang = lines[0]
            
            # Parse AST
            try:
                tree = ast.parse(content, filename=str(abs_path))
                analysis.ast_tree = tree
                
                # Perform detailed analysis
                self._extract_imports(tree, analysis, abs_path)
                self._extract_functions(tree, analysis)
                self._extract_classes(tree, analysis)
                self._extract_globals(tree, analysis)
                self._check_main_block(tree, analysis)
                self._calculate_complexity(tree, analysis)
                self._calculate_metrics(content, analysis)
                
                # Resolve dependencies
                self._resolve_dependencies(analysis)
                
                self.stats['parsed_files'] += 1
                
            except SyntaxError as e:
                analysis.errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
                self.stats['failed_files'] += 1
                
        except Exception as e:
            analysis.errors.append(f"Analysis error: {str(e)}")
            self.stats['failed_files'] += 1
        
        self.file_analyses[rel_path] = analysis
        return analysis

    def _extract_imports(self, tree: ast.AST, analysis: FileAnalysis, path: Path) -> None:
        """Extract all import statements with detailed information."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import x, import x as y
                for alias in node.names:
                    import_stmt = ImportStatement(
                        module=alias.name,
                        names=[alias.name],
                        aliases={alias.name: alias.asname} if alias.asname else {},
                        level=0,
                        import_type=ImportType.ALIASED if alias.asname else ImportType.ABSOLUTE,
                        line_number=node.lineno,
                        col_offset=node.col_offset,
                        raw_statement=ast.unparse(node)
                    )
                    analysis.imports.append(import_stmt)
                    self.stats['total_imports'] += 1
            
            elif isinstance(node, ast.ImportFrom):
                # Handle: from x import y, from .x import y
                if node.module == '__future__':
                    is_future = True
                else:
                    is_future = False
                
                names = [n.name for n in node.names]
                aliases = {n.name: n.asname for n in node.names if n.asname}
                
                # Determine import type
                if node.level > 0:
                    import_type = ImportType.RELATIVE
                elif '*' in names:
                    import_type = ImportType.WILDCARD
                elif aliases:
                    import_type = ImportType.ALIASED
                else:
                    import_type = ImportType.ABSOLUTE
                
                # Check if import is conditional (inside if/try block)
                parent_type = None
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        if child == node:
                            if isinstance(parent, (ast.If, ast.Try)):
                                parent_type = type(parent).__name__
                                import_type = ImportType.CONDITIONAL
                            break
                
                import_stmt = ImportStatement(
                    module=node.module,
                    names=names,
                    aliases=aliases,
                    level=node.level,
                    import_type=import_type,
                    line_number=node.lineno,
                    col_offset=node.col_offset,
                    raw_statement=ast.unparse(node),
                    is_future_import=is_future,
                    parent_node_type=parent_type
                )
                
                analysis.imports.append(import_stmt)
                self.stats['total_imports'] += 1
                
                # Warn about wildcard imports
                if '*' in names and not is_future:
                    analysis.warnings.append(
                        f"Wildcard import at line {node.lineno}: {ast.unparse(node)}"
                    )

    def _extract_functions(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract all function definitions with metadata."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get arguments
                args = []
                if node.args.args:
                    args = [arg.arg for arg in node.args.args]
                if node.args.kwonlyargs:
                    args.extend([arg.arg for arg in node.args.kwonlyargs])
                
                # Get decorators
                decorators = [ast.unparse(d) for d in node.decorator_list]
                
                # Get docstring
                docstring = ast.get_docstring(node)
                
                # Extract function calls
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            calls.append(child.func.attr)
                
                func_info = FunctionInfo(
                    name=node.name,
                    line_number=node.lineno,
                    args=args,
                    decorators=decorators,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    is_method=False,  # Will be updated when processing classes
                    docstring=docstring,
                    complexity=self._calculate_cyclomatic_complexity(node),
                    calls=calls
                )
                
                analysis.functions.append(func_info)
                self.stats['total_functions'] += 1

    def _extract_classes(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract all class definitions with metadata."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get base classes
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(ast.unparse(base))
                
                # Get decorators
                decorators = [ast.unparse(d) for d in node.decorator_list]
                is_dataclass = any('dataclass' in d for d in decorators)
                
                # Get methods
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(item.name)
                        # Mark functions as methods
                        for func in analysis.functions:
                            if func.name == item.name and func.line_number == item.lineno:
                                func.is_method = True
                
                # Get class attributes
                attributes = []
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        attributes.append(item.target.id)
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attributes.append(target.id)
                
                # Get docstring
                docstring = ast.get_docstring(node)
                
                class_info = ClassInfo(
                    name=node.name,
                    line_number=node.lineno,
                    bases=bases,
                    decorators=decorators,
                    methods=methods,
                    docstring=docstring,
                    is_dataclass=is_dataclass,
                    attributes=attributes
                )
                
                analysis.classes.append(class_info)
                self.stats['total_classes'] += 1

    def _extract_globals(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Extract global variables."""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis.global_variables.append(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                analysis.global_variables.append(node.target.id)

    def _check_main_block(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Check if file has if __name__ == '__main__' block."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    left = node.test.left
                    if isinstance(left, ast.Name) and left.id == '__name__':
                        for comp in node.test.comparators:
                            if isinstance(comp, ast.Constant) and comp.value == '__main__':
                                analysis.has_main_block = True
                                return

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
        
        return complexity

    def _calculate_complexity(self, tree: ast.AST, analysis: FileAnalysis) -> None:
        """Calculate overall complexity metrics."""
        total_complexity = 0
        max_depth = 0
        
        def get_nesting_depth(node, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    get_nesting_depth(child, depth + 1)
                else:
                    get_nesting_depth(child, depth)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                total_complexity += complexity
        
        get_nesting_depth(tree)
        
        analysis.metrics.cyclomatic_complexity = total_complexity
        analysis.metrics.max_nesting_depth = max_depth

    def _calculate_metrics(self, content: str, analysis: FileAnalysis) -> None:
        """Calculate comprehensive code metrics."""
        lines = content.split('\n')
        
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        docstring_lines = 0
        
        in_multiline_string = False
        quote_char = None
        
        for line in lines:
            stripped = line.strip()
            
            # Check for docstrings
            if '"""' in stripped or "'''" in stripped:
                if not in_multiline_string:
                    in_multiline_string = True
                    quote_char = '"""' if '"""' in stripped else "'''"
                    docstring_lines += 1
                elif quote_char in stripped:
                    in_multiline_string = False
                    docstring_lines += 1
                else:
                    docstring_lines += 1
                continue
            
            if in_multiline_string:
                docstring_lines += 1
                continue
            
            if not stripped:
                blank_lines += 1
            elif stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1
        
        analysis.metrics.total_lines = len(lines)
        analysis.metrics.code_lines = code_lines
        analysis.metrics.comment_lines = comment_lines
        analysis.metrics.blank_lines = blank_lines
        analysis.metrics.docstring_lines = docstring_lines
        analysis.metrics.function_count = len(analysis.functions)
        analysis.metrics.class_count = len(analysis.classes)
        analysis.metrics.method_count = sum(1 for f in analysis.functions if f.is_method)
        analysis.metrics.import_count = len(analysis.imports)
        
        # Calculate average function length
        if analysis.functions:
            analysis.metrics.avg_function_length = code_lines / len(analysis.functions)

    def _resolve_dependencies(self, analysis: FileAnalysis) -> None:
        """Resolve all imports to actual file dependencies."""
        if not analysis.module_name:
            return
        
        for imp in analysis.imports:
            resolved_path = self._resolve_import(imp, analysis.module_name)
            if resolved_path:
                try:
                    rel_path = str(Path(resolved_path).relative_to(self.repo_root))
                    # Don't add self-dependencies
                    if rel_path != analysis.file_path:
                        analysis.dependencies.add(rel_path)
                except ValueError:
                    pass  # External dependency

    def _resolve_import(self, imp: ImportStatement, current_module: str) -> Optional[str]:
        """
        Resolve an import statement to its actual file path.
        Handles both relative and absolute imports.
        """
        target_module = ""
        
        # CASE 1: Relative import (from ..package import module)
        if imp.level > 0:
            if not current_module:
                return None
            
            parts = current_module.split('.')
            
            # Check if going up too many levels
            if imp.level > len(parts):
                return None
            
            # Calculate base package
            if imp.level == len(parts):
                base = ""
            else:
                base = '.'.join(parts[:-imp.level])
            
            if base and imp.module:
                target_module = f"{base}.{imp.module}"
            elif base:
                target_module = base
            elif imp.module:
                target_module = imp.module
            else:
                return None
        
        # CASE 2: Absolute import
        else:
            if not imp.module:
                return None
            target_module = imp.module
        
        # Try to resolve the module
        # Attempt 1: Direct match
        if target_module in self.module_map:
            return self.module_map[target_module]
        
        # Attempt 2: It might be a package (__init__.py)
        init_module = f"{target_module}.__init__"
        if init_module in self.module_map:
            return self.module_map[init_module]
        
        # Attempt 3: Check if imported names are submodules
        for name in imp.names:
            if name == '*':
                continue
            potential_module = f"{target_module}.{name}"
            if potential_module in self.module_map:
                return self.module_map[potential_module]
        
        return None

    def get_dependency_graph(self, files: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Build complete dependency graph for specified files or all analyzed files.
        
        Args:
            files: List of file paths to include, or None for all files
            
        Returns:
            Dictionary mapping file paths to their dependencies
        """
        if files is None:
            files = list(self.file_analyses.keys())
        
        graph = {}
        
        for file_path in files:
            if file_path not in self.file_analyses:
                # Analyze if not already done
                self.analyze_file(file_path)
            
            if file_path in self.file_analyses:
                analysis = self.file_analyses[file_path]
                graph[file_path] = sorted(list(analysis.dependencies))
                
                # Update forward and reverse graphs
                self.dependency_graph[file_path] = analysis.dependencies
                for dep in analysis.dependencies:
                    self.reverse_dependency_graph[dep].add(file_path)
        
        return graph

    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies in the codebase.
        
        Returns:
            List of circular dependency chains
        """
        def find_cycle(node, path, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in self.dependency_graph:
                for neighbor in self.dependency_graph[node]:
                    if neighbor not in visited:
                        result = find_cycle(neighbor, path.copy(), visited, rec_stack)
                        if result:
                            return result
                    elif neighbor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        visited = set()
        cycles = []
        
        for node in self.dependency_graph:
            if node not in visited:
                cycle = find_cycle(node, [], visited, set())
                if cycle and cycle not in cycles:
                    cycles.append(cycle)
        
        return cycles

    def find_unused_imports(self, file_path: str) -> List[ImportStatement]:
        """
        Find imports that are not used in the file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of unused import statements
        """
        if file_path not in self.file_analyses:
            self.analyze_file(file_path)
        
        analysis = self.file_analyses.get(file_path)
        if not analysis or not analysis.ast_tree:
            return []
        
        # Collect all names used in the file
        used_names = set()
        for node in ast.walk(analysis.ast_tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # Check which imports are unused
        unused = []
        for imp in analysis.imports:
            # Skip wildcard imports
            if '*' in imp.names:
                continue
            
            # Check if any imported name is used
            imported_names = set(imp.names)
            if imp.aliases:
                imported_names.update(imp.aliases.values())
            
            if not imported_names.intersection(used_names):
                unused.append(imp)
        
        return unused

    def get_file_impact_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze the impact of changing a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with impact analysis
        """
        if file_path not in self.reverse_dependency_graph:
            return {
                'file': file_path,
                'direct_dependents': [],
                'transitive_dependents': [],
                'total_impact': 0
            }
        
        direct = self.reverse_dependency_graph[file_path]
        
        # Find transitive dependents
        transitive = set()
        to_visit = list(direct)
        visited = set()
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            transitive.add(current)
            
            if current in self.reverse_dependency_graph:
                to_visit.extend(self.reverse_dependency_graph[current])
        
        return {
            'file': file_path,
            'direct_dependents': sorted(list(direct)),
            'transitive_dependents': sorted(list(transitive - direct)),
            'total_impact': len(transitive)
        }

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a comprehensive analysis report.
        
        Args:
            output_file: Optional path to write report to
            
        Returns:
            Report as string
        """
        report_lines = [
            "=" * 80,
            "PYTHON CODE ANALYSIS REPORT",
            "=" * 80,
            "",
            f"Repository: {self.repo_root}",
            f"Total Files: {self.stats['total_files']}",
            f"Successfully Parsed: {self.stats['parsed_files']}",
            f"Failed to Parse: {self.stats['failed_files']}",
            f"Total Imports: {self.stats['total_imports']}",
            f"Total Functions: {self.stats['total_functions']}",
            f"Total Classes: {self.stats['total_classes']}",
            "",
            "=" * 80,
            "CIRCULAR DEPENDENCIES",
            "=" * 80,
        ]
        
        cycles = self.find_circular_dependencies()
        if not cycles:
            report_lines.append("None detected.")
        else:
            for i, cycle in enumerate(cycles, 1):
                report_lines.append(f"{i}. {' -> '.join(cycle)}")
        
        return "\n".join(report_lines)