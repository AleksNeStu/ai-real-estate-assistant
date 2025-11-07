"""
Ollama Detection and Installation Guidance Utility.

Provides functionality to:
- Detect if Ollama is installed locally
- Check if Ollama service is running
- Provide OS-specific installation instructions
- Get available models
"""

import platform
import subprocess
import requests
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass


@dataclass
class OllamaStatus:
    """Status of Ollama installation and service."""
    is_installed: bool
    is_running: bool
    version: Optional[str] = None
    base_url: str = "http://localhost:11434"
    available_models: List[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.available_models is None:
            self.available_models = []


class OllamaDetector:
    """Utility class for detecting and managing Ollama installation."""

    DEFAULT_BASE_URL = "http://localhost:11434"

    @staticmethod
    def get_os_type() -> str:
        """
        Get the current operating system type.

        Returns:
            str: 'macos', 'linux', or 'windows'
        """
        system = platform.system().lower()
        if system == 'darwin':
            return 'macos'
        elif system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        return 'unknown'

    @staticmethod
    def check_ollama_installed() -> bool:
        """
        Check if Ollama is installed by trying to run 'ollama --version'.

        Returns:
            bool: True if Ollama is installed, False otherwise
        """
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    @staticmethod
    def get_ollama_version() -> Optional[str]:
        """
        Get the installed Ollama version.

        Returns:
            Optional[str]: Version string if available, None otherwise
        """
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Output is typically "ollama version 0.X.X"
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return None

    @staticmethod
    def check_ollama_running(base_url: str = DEFAULT_BASE_URL) -> bool:
        """
        Check if Ollama service is running by hitting the API.

        Args:
            base_url: Base URL for Ollama API

        Returns:
            bool: True if service is running, False otherwise
        """
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except (requests.RequestException, Exception):
            return False

    @staticmethod
    def get_available_models(base_url: str = DEFAULT_BASE_URL) -> List[str]:
        """
        Get list of models available in Ollama.

        Args:
            base_url: Base URL for Ollama API

        Returns:
            List[str]: List of model names
        """
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return [model.get('name', '') for model in models if model.get('name')]
            return []
        except (requests.RequestException, Exception):
            return []

    @classmethod
    def get_status(cls, base_url: str = DEFAULT_BASE_URL) -> OllamaStatus:
        """
        Get comprehensive Ollama status.

        Args:
            base_url: Base URL for Ollama API

        Returns:
            OllamaStatus: Complete status information
        """
        is_installed = cls.check_ollama_installed()
        is_running = False
        version = None
        available_models = []
        error_message = None

        if is_installed:
            version = cls.get_ollama_version()
            is_running = cls.check_ollama_running(base_url)

            if is_running:
                available_models = cls.get_available_models(base_url)
            else:
                error_message = "Ollama is installed but not running. Start it with 'ollama serve'"
        else:
            error_message = "Ollama is not installed"

        return OllamaStatus(
            is_installed=is_installed,
            is_running=is_running,
            version=version,
            base_url=base_url,
            available_models=available_models,
            error_message=error_message
        )

    @staticmethod
    def get_installation_instructions(os_type: Optional[str] = None) -> Dict[str, any]:
        """
        Get OS-specific installation instructions for Ollama.

        Args:
            os_type: Operating system type ('macos', 'linux', 'windows', or None for auto-detect)

        Returns:
            Dict containing installation instructions, commands, and URLs
        """
        if os_type is None:
            os_type = OllamaDetector.get_os_type()

        instructions = {
            'macos': {
                'title': '🍎 macOS Installation',
                'method_1': {
                    'name': 'Download Installer (Recommended)',
                    'steps': [
                        'Visit https://ollama.com/download',
                        'Download Ollama for macOS',
                        'Open the downloaded .dmg file',
                        'Drag Ollama to Applications folder',
                        'Launch Ollama from Applications'
                    ],
                    'url': 'https://ollama.com/download'
                },
                'method_2': {
                    'name': 'Homebrew',
                    'command': 'brew install ollama',
                    'steps': [
                        'Open Terminal',
                        'Run: brew install ollama',
                        'Start Ollama: ollama serve'
                    ]
                },
                'post_install': [
                    'Verify installation: ollama --version',
                    'Pull a model: ollama pull llama3.3:8b',
                    'Test: ollama run llama3.3:8b'
                ]
            },
            'linux': {
                'title': '🐧 Linux Installation',
                'method_1': {
                    'name': 'One-line Install (Recommended)',
                    'command': 'curl -fsSL https://ollama.com/install.sh | sh',
                    'steps': [
                        'Open Terminal',
                        'Run the install script:',
                        'curl -fsSL https://ollama.com/install.sh | sh',
                        'Start Ollama: ollama serve'
                    ],
                    'url': 'https://ollama.com/download'
                },
                'method_2': {
                    'name': 'Manual Installation',
                    'steps': [
                        'Visit https://ollama.com/download',
                        'Download the Linux binary',
                        'Make it executable: chmod +x ollama',
                        'Move to PATH: sudo mv ollama /usr/local/bin/',
                        'Start service: ollama serve'
                    ]
                },
                'post_install': [
                    'Verify: ollama --version',
                    'Enable systemd service (optional):',
                    'sudo systemctl enable ollama',
                    'sudo systemctl start ollama',
                    'Pull a model: ollama pull llama3.3:8b'
                ]
            },
            'windows': {
                'title': '🪟 Windows Installation',
                'method_1': {
                    'name': 'Download Installer (Recommended)',
                    'steps': [
                        'Visit https://ollama.com/download',
                        'Download Ollama for Windows',
                        'Run the installer (.exe file)',
                        'Follow installation wizard',
                        'Ollama will start automatically'
                    ],
                    'url': 'https://ollama.com/download'
                },
                'method_2': {
                    'name': 'Windows Package Manager (winget)',
                    'command': 'winget install Ollama.Ollama',
                    'steps': [
                        'Open PowerShell or Command Prompt',
                        'Run: winget install Ollama.Ollama',
                        'Ollama will start automatically'
                    ]
                },
                'post_install': [
                    'Open Command Prompt or PowerShell',
                    'Verify: ollama --version',
                    'Pull a model: ollama pull llama3.3:8b',
                    'Test: ollama run llama3.3:8b'
                ]
            },
            'unknown': {
                'title': '❓ Installation Instructions',
                'message': 'Visit https://ollama.com/download for installation instructions for your platform.',
                'url': 'https://ollama.com/download'
            }
        }

        return instructions.get(os_type, instructions['unknown'])

    @staticmethod
    def get_recommended_models() -> List[Dict[str, str]]:
        """
        Get list of recommended models to install.

        Returns:
            List[Dict]: List of model information
        """
        return [
            {
                'name': 'llama3.3:8b',
                'size': '4.9 GB',
                'ram': '8 GB',
                'description': 'Latest Llama 3.3 - Best overall performance',
                'command': 'ollama pull llama3.3:8b',
                'recommended': True
            },
            {
                'name': 'llama3.2:3b',
                'size': '2.0 GB',
                'ram': '4 GB',
                'description': 'Lightweight - Great for limited resources',
                'command': 'ollama pull llama3.2:3b',
                'recommended': True
            },
            {
                'name': 'mistral:7b',
                'size': '4.1 GB',
                'ram': '8 GB',
                'description': 'Excellent for general tasks',
                'command': 'ollama pull mistral:7b',
                'recommended': False
            },
            {
                'name': 'qwen2.5:7b',
                'size': '4.7 GB',
                'ram': '8 GB',
                'description': 'Strong multilingual support',
                'command': 'ollama pull qwen2.5:7b',
                'recommended': False
            }
        ]
