#!/usr/bin/env python3
"""
Find all missing dependencies in the backend
Distinguished Engineer Implementation - Complete dependency analysis
"""

import os
import ast
import importlib.util

def find_all_imports(file_path):
    """Extract all imports from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
    except:
        return []
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def check_import_exists(module_name, base_path='backend'):
    """Check if an import can be resolved"""
    # Check if it's a local module
    if module_name.startswith(('services.', 'api.', 'config.', 'models.', 'database.', 'schemas.', 'middleware.')):
        # Convert to file path
        parts = module_name.split('.')
        file_path = os.path.join(base_path, *parts) + '.py'
        dir_path = os.path.join(base_path, *parts)
        
        # Check if it's a file or directory with __init__.py
        if os.path.exists(file_path):
            return True, file_path
        elif os.path.exists(dir_path) and os.path.exists(os.path.join(dir_path, '__init__.py')):
            return True, dir_path
        else:
            return False, None
    else:
        # It's an external package, check if it can be imported
        try:
            spec = importlib.util.find_spec(module_name.split('.')[0])
            return spec is not None, None
        except:
            return False, None

def scan_file(file_path):
    """Scan a single file for missing dependencies"""
    print(f"\n📄 Checking: {file_path}")
    imports = find_all_imports(file_path)
    
    missing = []
    found = []
    
    for imp in imports:
        exists, path = check_import_exists(imp)
        if not exists:
            missing.append(imp)
            print(f"  ❌ MISSING: {imp}")
        else:
            found.append(imp)
    
    return missing, found

def main():
    """Main dependency check"""
    
    print("=" * 60)
    print("🔍 CHECKING MAIN.PY DEPENDENCIES")
    print("=" * 60)

    # Check main.py specifically
    missing_main, found_main = scan_file('backend/main.py')

    print("\n" + "=" * 60)
    print("📊 MAIN.PY SUMMARY")
    print("=" * 60)
    print(f"✅ Found imports: {len(found_main)}")
    print(f"❌ Missing imports: {len(missing_main)}")

    if missing_main:
        print("\n🚨 MISSING DEPENDENCIES IN MAIN.PY:")
        
        # Group by category
        services_missing = [m for m in missing_main if m.startswith('services.')]
        api_missing = [m for m in missing_main if m.startswith('api.')]
        config_missing = [m for m in missing_main if m.startswith('config.')]
        models_missing = [m for m in missing_main if m.startswith('models.')]
        middleware_missing = [m for m in missing_main if m.startswith('middleware.')]
        database_missing = [m for m in missing_main if m.startswith('database.')]
        external_missing = [m for m in missing_main if not m.startswith(('services.', 'api.', 'config.', 'models.', 'middleware.', 'database.'))]
        
        if services_missing:
            print("\n  🔧 Missing Services:")
            for imp in sorted(services_missing):
                print(f"    - {imp}")
        
        if api_missing:
            print("\n  🌐 Missing API modules:")
            for imp in sorted(api_missing):
                print(f"    - {imp}")
        
        if middleware_missing:
            print("\n  🛡️ Missing Middleware:")
            for imp in sorted(middleware_missing):
                print(f"    - {imp}")
        
        if database_missing:
            print("\n  🗄️ Missing Database:")
            for imp in sorted(database_missing):
                print(f"    - {imp}")
        
        if config_missing:
            print("\n  ⚙️ Missing Config:")
            for imp in sorted(config_missing):
                print(f"    - {imp}")
        
        if models_missing:
            print("\n  🤖 Missing Models:")
            for imp in sorted(models_missing):
                print(f"    - {imp}")
        
        if external_missing:
            print("\n  📦 Missing External packages:")
            for imp in sorted(external_missing):
                print(f"    - {imp}")

    # Check requirements.txt
    print("\n" + "=" * 60)
    print("📦 CHECKING REQUIREMENTS.TXT")
    print("=" * 60)

    req_files = ['backend/requirements.txt', 'backend/requirements.prod.txt']
    all_requirements = set()
    
    for req_file in req_files:
        if os.path.exists(req_file):
            print(f"\n📄 Checking {req_file}:")
            with open(req_file, 'r') as f:
                requirements = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        pkg = line.split('>=')[0].split('==')[0].split('[')[0]
                        requirements.append(pkg)
                        all_requirements.add(pkg)
                
            print(f"  Packages: {len(requirements)}")
            for req in requirements:
                print(f"    - {req}")

    # Check if external missing packages are in requirements
    if external_missing:
        print("\n" + "=" * 60)
        print("🔍 EXTERNAL PACKAGE ANALYSIS")
        print("=" * 60)
        
        for pkg in sorted(external_missing):
            base_pkg = pkg.split('.')[0]
            if base_pkg in all_requirements:
                print(f"  ✅ {pkg} -> {base_pkg} (in requirements)")
            else:
                print(f"  ❌ {pkg} -> {base_pkg} (NOT in requirements)")

    # Generate fix commands
    print("\n" + "=" * 60)
    print("🔧 RECOMMENDED FIXES")
    print("=" * 60)
    
    if external_missing:
        missing_packages = set()
        for pkg in external_missing:
            base_pkg = pkg.split('.')[0]
            if base_pkg not in all_requirements:
                missing_packages.add(base_pkg)
        
        if missing_packages:
            print("\n📦 Add these to requirements.prod.txt:")
            for pkg in sorted(missing_packages):
                print(f"  {pkg}>=1.0.0")
    
    if services_missing or api_missing:
        print("\n🔧 Comment out these imports in main.py:")
        for imp in sorted(services_missing + api_missing):
            print(f"  # from {imp} import ...")
    
    print("\n" + "=" * 60)
    print("✅ DEPENDENCY CHECK COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
