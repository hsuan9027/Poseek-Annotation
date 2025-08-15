"""
ConfigManager - Handles configuration management
Manages configuration files, keypoint editing, and user settings
"""

import os
import yaml
from PySide6.QtCore import QObject, Signal
from gui.utils import load_config, save_config
from gui.components import KeypointEditor


class ConfigManager(QObject):
    """Configuration manager for all config-related operations"""
    
    # Signals
    config_updated = Signal(dict)           # Configuration updated
    keypoints_updated = Signal(list, list)  # Keypoints updated (bodyparts, connections)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Configuration data
        self.config = {}
        self.bodyparts = []
        self.connections = []
        
        # Configuration file paths
        self.config_path = None
        self.keypoints_config_path = None
        
        # Keypoint editor
        self.keypoint_editor = None
        
        # Initialize configuration paths
        self._init_config_paths()
    
    def _init_config_paths(self):
        """Initialize configuration file paths"""
        # Get project root directory
        if self.parent:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        else:
            project_root = os.getcwd()
        
        # Set configuration file paths
        self.config_path = os.path.join(project_root, 'train_cfg.yaml')
        self.keypoints_config_path = os.path.join(project_root, 'keypoints_cfg.yaml')
    
    def load_main_config(self):
        """Load main configuration file"""
        try:
            self.config = load_config(self.config_path)
            if self.config:
                # Extract keypoint configuration
                keypoints_config = self.config.get('keypoints', {})
                self.bodyparts = keypoints_config.get('bodyparts', [])
                self.connections = keypoints_config.get('connections', [])
                
                # Emit configuration update signals
                self.config_updated.emit(self.config)
                self.keypoints_updated.emit(self.bodyparts, self.connections)
                
                return True
        except Exception as e:
            print(f"Error loading main config: {str(e)}")
        
        return False
    
    def save_main_config(self):
        """Save main configuration file"""
        try:
            # Update keypoint info in configuration
            if 'keypoints' not in self.config:
                self.config['keypoints'] = {}
            
            self.config['keypoints']['bodyparts'] = self.bodyparts
            self.config['keypoints']['connections'] = self.connections
            
            # Update keypoint count in model
            if 'model' in self.config and 'n_keypoints' in self.config['model']:
                self.config['model']['n_keypoints'] = len(self.bodyparts)
            
            # Save configuration
            save_config(self.config_path, self.config)
            return True
            
        except Exception as e:
            print(f"Error saving main config: {str(e)}")
            return False
    
    def load_saved_configs(self):
        """Load saved keypoint configurations"""
        try:
            if os.path.exists(self.keypoints_config_path):
                with open(self.keypoints_config_path, 'r', encoding='utf-8') as f:
                    configs = yaml.safe_load(f)
                return configs if isinstance(configs, dict) else {}
        except Exception as e:
            print(f"Error loading saved configs: {str(e)}")
        
        return {}
    
    def save_keypoints_config(self, configs):
        """Save keypoint configuration to file"""
        try:
            save_config(self.keypoints_config_path, configs)
            return True
        except Exception as e:
            print(f"Error saving keypoints config: {str(e)}")
            return False
    
    def edit_keypoints(self):
        """Open keypoint editing dialog"""
        if not self.parent:
            return
        
        # Create keypoint editor
        self.keypoint_editor = KeypointEditor(
            parent=self.parent,
            config=self.config,
            bodyparts=self.bodyparts.copy(),
            connections=self.connections.copy(),
            keypoints_config_path=self.keypoints_config_path
        )
        
        # Open editor
        self.keypoint_editor.open_editor()
        
        # Check for updates
        self._check_for_config_updates()
    
    def _check_for_config_updates(self):
        """Check for configuration updates"""
        # Reload configuration
        old_bodyparts = self.bodyparts.copy()
        old_connections = self.connections.copy()
        
        # Get latest data from configuration
        if self.load_main_config():
            # Check for changes
            if (self.bodyparts != old_bodyparts or 
                self.connections != old_connections):
                # Emit update signal
                self.keypoints_updated.emit(self.bodyparts, self.connections)
    
    def update_keypoints_config(self, bodyparts, connections, config_name=None):
        """Update keypoint configuration"""
        self.bodyparts = bodyparts.copy() if bodyparts else []
        self.connections = connections.copy() if connections else []
        
        # Update main configuration
        if 'keypoints' not in self.config:
            self.config['keypoints'] = {}
        
        self.config['keypoints']['bodyparts'] = self.bodyparts
        self.config['keypoints']['connections'] = self.connections
        
        if config_name:
            self.config['keypoints']['name'] = config_name
        
        # Update model configuration
        if 'model' in self.config:
            self.config['model']['n_keypoints'] = len(self.bodyparts)
        
        # Save configuration
        self.save_main_config()
        
        # Emit update signals
        self.keypoints_updated.emit(self.bodyparts, self.connections)
        self.config_updated.emit(self.config)
    
    def get_config(self):
        """Get current configuration"""
        return self.config.copy()
    
    def get_keypoints_config(self):
        """Get keypoint configuration"""
        return {
            'bodyparts': self.bodyparts.copy(),
            'connections': self.connections.copy()
        }
    
    def get_bodyparts(self):
        """Get bodypart list"""
        return self.bodyparts.copy()
    
    def get_connections(self):
        """Get connection list"""
        return self.connections.copy()
    
    def set_bodyparts(self, bodyparts):
        """Set bodypart list"""
        self.bodyparts = bodyparts.copy()
    
    def set_connections(self, connections):
        """Set connection list"""
        self.connections = connections.copy()
    
    def set_config_path(self, config_path):
        """Set configuration file path"""
        self.config_path = config_path
    
    def set_keypoints_config_path(self, keypoints_config_path):
        """Set keypoint configuration file path"""
        self.keypoints_config_path = keypoints_config_path
    
    def reset_config(self):
        """Reset configuration to default state"""
        self.config = {}
        self.bodyparts = []
        self.connections = []
        
        # Emit update signals
        self.keypoints_updated.emit(self.bodyparts, self.connections)
        self.config_updated.emit(self.config)
    
    def import_config_from_file(self, file_path):
        """Import configuration from file"""
        try:
            imported_config = load_config(file_path)
            if imported_config:
                self.config = imported_config
                
                # Extract keypoint configuration
                keypoints_config = self.config.get('keypoints', {})
                self.bodyparts = keypoints_config.get('bodyparts', [])
                self.connections = keypoints_config.get('connections', [])
                
                # Emit update signal
                self.config_updated.emit(self.config)
                self.keypoints_updated.emit(self.bodyparts, self.connections)
                
                return True
        except Exception as e:
            print(f"Error importing config from {file_path}: {str(e)}")
        
        return False
    
    def export_config_to_file(self, file_path):
        """Export configuration to file"""
        try:
            save_config(file_path, self.config)
            return True
        except Exception as e:
            print(f"Error exporting config to {file_path}: {str(e)}")
            return False
    
    def validate_config(self):
        """Validate configuration validity"""
        errors = []
        
        # Check required fields
        if not isinstance(self.config, dict):
            errors.append("Config must be a dictionary")
            return errors
        
        # Check keypoint configuration
        if 'keypoints' in self.config:
            keypoints = self.config['keypoints']
            
            if 'bodyparts' in keypoints:
                if not isinstance(keypoints['bodyparts'], list):
                    errors.append("Bodyparts must be a list")
                elif len(keypoints['bodyparts']) == 0:
                    errors.append("Bodyparts list cannot be empty")
            
            if 'connections' in keypoints:
                if not isinstance(keypoints['connections'], list):
                    errors.append("Connections must be a list")
                else:
                    # Validate connection validity
                    num_bodyparts = len(keypoints.get('bodyparts', []))
                    for i, conn in enumerate(keypoints['connections']):
                        if not isinstance(conn, list) or len(conn) != 2:
                            errors.append(f"Connection {i} must be a list of 2 indices")
                        elif (not isinstance(conn[0], int) or not isinstance(conn[1], int) or
                              conn[0] < 0 or conn[1] < 0 or 
                              conn[0] >= num_bodyparts or conn[1] >= num_bodyparts):
                            errors.append(f"Connection {i} has invalid indices")
        
        # Check model configuration
        if 'model' in self.config:
            model = self.config['model']
            
            if 'n_keypoints' in model:
                expected_n_keypoints = len(self.bodyparts)
                if model['n_keypoints'] != expected_n_keypoints:
                    errors.append(f"Model n_keypoints ({model['n_keypoints']}) doesn't match bodyparts count ({expected_n_keypoints})")
        
        return errors
    
    def get_config_summary(self):
        """Get configuration summary information"""
        summary = {
            'total_bodyparts': len(self.bodyparts),
            'total_connections': len(self.connections),
            'config_name': self.config.get('keypoints', {}).get('name', 'Unnamed'),
            'model_keypoints': self.config.get('model', {}).get('n_keypoints', 0),
            'has_model_config': 'model' in self.config,
            'has_training_config': 'training' in self.config,
            'config_path': self.config_path,
            'keypoints_config_path': self.keypoints_config_path
        }
        
        return summary