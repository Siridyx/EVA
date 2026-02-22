"""
Example Plugin — Plugin d'exemple pour EVA

Démontre comment créer un plugin simple.

Ce plugin enregistre un tool "greet" qui salue l'utilisateur.
"""

from eva.plugins import PluginBase


class ExamplePlugin(PluginBase):
    """
    Plugin d'exemple.
    
    Enregistre un tool simple pour démonstration.
    """
    
    plugin_id = "example"
    plugin_version = "1.0.0"
    
    def setup(self, context):
        """
        Configure le plugin.
        
        Enregistre le tool "greet" dans le registry.
        """
        # Enregistrer tool
        context.registry.register_tool("greet", self.greet)
        
        # Event custom (optionnel)
        self.emit("example_plugin_ready", {
            "message": "Example plugin loaded successfully"
        })
    
    def greet(self, name: str) -> str:
        """
        Salue une personne.
        
        Args:
            name: Nom de la personne
        
        Returns:
            Message de salutation
        
        Example:
            >>> greet("Alice")
            "Hello, Alice! Welcome to EVA."
        """
        return f"Hello, {name}! Welcome to EVA."


def get_plugin(config, event_bus):
    """
    Point d'entrée du plugin.
    
    Args:
        config: ConfigManager
        event_bus: EventBus
    
    Returns:
        Instance du plugin
    """
    return ExamplePlugin(config, event_bus)