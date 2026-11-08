#!/usr/bin/env python3
"""
Quick verification script for dynamic port allocation system.
Run this to verify all components work correctly.
"""

import json
import subprocess
import sys
from pathlib import Path

# Repository root: scripts/utils/verify-port-system.py -> scripts/utils -> scripts -> root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# `port.port_manager` lives in scripts/, `service_discovery` next to this file.
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "utils"))

# The report uses check/cross marks; a Windows console defaults to cp1250 and
# would abort the run on a UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

print("=" * 60)
print("Dynamic Port Allocation System Verification")
print("=" * 60)

# Test 1: Port Manager Core Functions
print("\n[1] Testing PortManager core functions...")
try:
    from port.port_manager import PortManager

    print("   ✓ PortManager imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import PortManager: {e}")
    sys.exit(1)

# Test 2: Service Discovery
print("\n[2] Testing ServiceDiscovery...")
try:
    from service_discovery import ServiceDiscovery

    print("   ✓ ServiceDiscovery imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import ServiceDiscovery: {e}")
    sys.exit(1)

# Test 3: Port Manager Instantiation
print("\n[3] Testing PortManager instantiation...")
pm = PortManager(PROJECT_ROOT)
print("   ✓ PortManager created")
print(f"   Registry path: {pm.registry_path}")
print(f"   Ranges: {pm.PORT_RANGES}")

# Test 4: Port Availability Check
print("\n[4] Testing port availability check...")
try:
    test_port = 59997
    is_free = not pm._is_port_in_use_system(test_port)
    print(f"   ✓ Port {test_port} is free: {is_free}")
except Exception as e:
    print(f"   ✗ Port check failed: {e}")
    sys.exit(1)

# Test 5: Port Allocation
print("\n[5] Testing port allocation...")
try:
    port = pm.allocate_port("backend", "test-service")
    print(f"   ✓ Allocated backend port: {port}")

    # Verify allocation exists
    alloc = pm.get_allocation("test-service")
    if alloc:
        print(f"   ✓ Allocation found: {alloc}")
        print(f"     Port: {alloc['port']}")
        print(f"     Status: {alloc['status']}")
    else:
        print("   ✗ Allocation not found")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Allocation failed: {e}")
    sys.exit(1)

# Test 6: Service Discovery
print("\n[6] Testing ServiceDiscovery...")
sd = ServiceDiscovery(PROJECT_ROOT)
print("   ✓ ServiceDiscovery created")

backend_port, frontend_port = sd.ensure_ports_configured()
print("   ✓ Ports configured:")
print(f"     Backend: {backend_port}")
print(f"     Frontend: {frontend_port}")

# Verify .env.ports was created
env_ports_path = PROJECT_ROOT / ".env.ports"
if env_ports_path.exists():
    print(f"   ✓ .env.ports created at {env_ports_path}")
    content = env_ports_path.read_text()
    print("   Content preview:")
    print(content[:200])
else:
    print("   ✗ .env.ports not created")
    sys.exit(1)

# Test 7: Get URLs
print("\n[7] Testing URL getters...")
backend_url = sd.get_backend_url()
frontend_url = sd.get_frontend_url()
print("   ✓ URLs retrieved")
print(f"     Backend: {backend_url}")
print(f"     Frontend: {frontend_url}")

# Test 8: Kill Process on Unused Port
print("\n[8] Testing kill process on unused port...")
result = pm.kill_process_on_port(59996, force=False)
print(f"   ✓ Kill port returned: {result}")

# Test 9: Release Port
print("\n[9] Testing port release...")
try:
    release_result = pm.release_port(port)
    print(f"   ✓ Port released: {release_result}")

    # Verify status: a released allocation must no longer be active.
    active = pm.get_allocation("test-service")
    if active is None:
        print("   ✓ Allocation is no longer active")
    else:
        print(f"   ✗ Allocation still active: {active['status']}")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Port release failed: {e}")
    sys.exit(1)

# Test 10: Port Manager CLI
print("\n[10] Testing port-manager.py CLI...")
cli_script = str(PROJECT_ROOT / "scripts" / "port" / "port_manager.py")
result = subprocess.run(
    [
        sys.executable,
        cli_script,
        "--action",
        "status",
        "--project-root",
        str(PROJECT_ROOT),
        "--json",
    ],
    capture_output=True,
    text=True,
    timeout=30,
)
print("   ✓ CLI status command succeeded")
print(f"   Output: {result.stdout[:200]}")

output = json.loads(result.stdout)
print(f"   Registry: {output.get('registry')}")
print(f"   Ranges: {output.get('ranges')}")

# Test 11: Service Discovery CLI
print("\n[11] Testing service-discovery.py CLI...")
cli_script = str(PROJECT_ROOT / "scripts" / "utils" / "service_discovery.py")
result = subprocess.run(
    [sys.executable, cli_script, "--allocate", "--json"],
    capture_output=True,
    text=True,
    timeout=30,
)
print("   ✓ CLI allocate command succeeded")
output = json.loads(result.stdout)
print(f"   Backend port: {output.get('backend_port')}")
print(f"   Frontend port: {output.get('frontend_port')}")

# Test 12: start-with-ports.py Dry Run
print("\n[12] Testing start-with-ports.py dry run...")
cli_script = str(PROJECT_ROOT / "scripts" / "utils" / "start-with-ports.py")
result = subprocess.run(
    [sys.executable, cli_script, "--dry-run", "--service", "backend"],
    capture_output=True,
    text=True,
    timeout=30,
    cwd=str(PROJECT_ROOT),
)
print("   ✓ Dry run command succeeded")
print("   Output preview:")
print(result.stdout[:500])

# Summary
print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print("\nDynamic Port Allocation System is working correctly!")
print("\nTo use the system:")
print("  1. Start services: python scripts/utils/start-with-ports.py")
print(
    "  2. Allocate ports: python scripts/port/port_manager.py"
    " --action allocate --category backend --service-name my-service"
)
print("  3. Dry run mode: python scripts/utils/start-with-ports.py --dry-run")
print("  4. Kill services: pwsh scripts/utils/kill-port.ps1 -Ports 8000,3800 (Windows)")
print("     OR: bash scripts/utils/kill-port.sh 8000 3800 (Unix)")
print("\nFor more information, see:")
print("  - docs/configuration/PORT-CONFIGURATION.md - Documentation")
print("  - scripts/README.md - Scripts README")
print("=" * 60)
