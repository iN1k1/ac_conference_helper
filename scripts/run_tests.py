#!/usr/bin/env python3
"""
Test runner for conference helper project.
Run all unit tests with a single command.
"""

import subprocess
import sys
import os

def run_tests():
    """Run all unit tests and return results."""
    test_files = [
        'tests/test_models.py',
        'tests/test_display.py', 
        'tests/test_openreview_client.py'
    ]
    
    results = {}
    total_passed = 0
    total_failed = 0
    total_tests = 0
    
    print("🧪 Running Conference Helper Unit Tests")
    print("=" * 50)
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ {test_file} not found")
            continue
            
        print(f"📋 Running {os.path.basename(test_file)}...")
        
        try:
            # Run pytest and capture output
            result = subprocess.run(
                ['uv', 'run', 'pytest', test_file, '-v', '--tb=short'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            # Parse results from pytest output
            output = result.stdout
            passed = output.count('PASSED')
            failed = output.count('FAILED')
            
            # Extract test counts from the summary line
            lines = output.split('\n')
            for line in lines:
                if 'passed in' in line and 'failed in' in line:
                    # Extract numbers from lines like "23 passed, 2 failed"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if i == 0:
                                passed = int(part)
                            elif i == 2:
                                failed = int(part)
                            elif 'passed' in part and 'failed' in part:
                                total_tests = passed + failed
            
            results[test_file] = {
                'passed': passed,
                'failed': failed,
                'total': total_tests,
                'exit_code': result.returncode
            }
            
            total_passed += passed
            total_failed += failed
            total_tests += total_tests
            
            if result.returncode == 0:
                print(f"✅ {os.path.basename(test_file)}: {passed}/{total_tests} tests passed")
            else:
                print(f"❌ {os.path.basename(test_file)}: {failed} tests failed")
                
        except Exception as e:
            print(f"💥 Error running {test_file}: {e}")
            results[test_file] = {
                'passed': 0,
                'failed': 1,
                'total': 1,
                'exit_code': 1
            }
            total_failed += 1
            total_tests += 1
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print(f"Total tests: {total_tests}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    
    if total_failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"💥 {total_failed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
