"""Tests unitaires pour PromptManager (R-013)"""

import pytest
from pathlib import Path
from eva.prompt.prompt_manager import PromptManager
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus


@pytest.fixture
def config():
    """Fixture ConfigManager."""
    return ConfigManager()


@pytest.fixture
def event_bus():
    """Fixture EventBus."""
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def clean_prompts(config):
    """Fixture pour nettoyer les prompts."""
    prompts_path = config.get_path("prompts")
    
    # Backup
    backups = []
    if prompts_path.exists():
        for f in prompts_path.glob("*.txt"):
            backups.append((f, f.read_text()))
            f.unlink()
    
    yield prompts_path
    
    # Restore
    for f, content in backups:
        f.write_text(content)


def test_prompt_manager_init(config, event_bus):
    """PromptManager s'initialise correctement."""
    pm = PromptManager(config, event_bus)
    
    assert pm.name == "PromptManager"
    assert pm.prompt_count == 0
    assert not pm.is_running


def test_prompt_manager_creates_default_prompts(config, event_bus, clean_prompts):
    """start() crée les prompts par défaut."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    assert pm.is_running
    assert pm.prompt_count >= 2  # system + system_concise
    
    # Vérifier fichiers créés
    system_file = clean_prompts / "system.txt"
    assert system_file.exists()
    
    pm.stop()


def test_prompt_manager_get(config, event_bus, clean_prompts):
    """get() récupère un prompt."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    prompt = pm.get("system")
    
    assert "EVA" in prompt
    assert "{{tone}}" in prompt
    assert "{{expertise}}" in prompt
    
    pm.stop()


def test_prompt_manager_get_before_start(config, event_bus):
    """get() avant start() raise."""
    pm = PromptManager(config, event_bus)
    
    with pytest.raises(RuntimeError, match="not started"):
        pm.get("system")


def test_prompt_manager_get_nonexistent(config, event_bus, clean_prompts):
    """get() prompt inexistant raise."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    with pytest.raises(FileNotFoundError, match="not found"):
        pm.get("nonexistent")
    
    pm.stop()


def test_prompt_manager_render(config, event_bus, clean_prompts):
    """render() remplace les variables."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    prompt = pm.render("system", tone="amical", expertise="Python")
    
    assert "amical" in prompt
    assert "Python" in prompt
    assert "{{tone}}" not in prompt
    assert "{{expertise}}" not in prompt
    
    pm.stop()


def test_prompt_manager_render_unresolved_placeholder(config, event_bus, clean_prompts):
    """render() avec placeholder non résolu raise."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Manque "expertise"
    with pytest.raises(ValueError, match="Unresolved placeholders"):
        pm.render("system", tone="amical")
    
    pm.stop()


def test_prompt_manager_render_extra_variables(config, event_bus, clean_prompts):
    """render() avec variables extra (pas d'erreur)."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Variables supplémentaires ignorées
    prompt = pm.render(
        "system",
        tone="amical",
        expertise="Python",
        extra="ignored"
    )
    
    assert "amical" in prompt
    assert "ignored" not in prompt
    
    pm.stop()


def test_prompt_manager_list_prompts(config, event_bus, clean_prompts):
    """list_prompts() retourne tous les prompts."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    prompts = pm.list_prompts()
    
    assert "system" in prompts
    assert "system_concise" in prompts
    assert len(prompts) >= 2
    
    pm.stop()


def test_prompt_manager_extract_variables(config, event_bus, clean_prompts):
    """extract_variables() retourne les variables du template."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    variables = pm.extract_variables("system")
    
    assert "tone" in variables
    assert "expertise" in variables
    
    pm.stop()


def test_prompt_manager_reload(config, event_bus, clean_prompts):
    """get(reload=True) recharge depuis disque."""
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Premier chargement
    prompt1 = pm.get("system")
    
    # Modifier le fichier
    system_file = clean_prompts / "system.txt"
    system_file.write_text("Modified {{tone}}", encoding="utf-8")
    
    # Recharger
    prompt2 = pm.get("system", reload=True)
    
    assert prompt1 != prompt2
    assert "Modified" in prompt2
    
    pm.stop()


def test_prompt_manager_emits_events(config, event_bus, clean_prompts):
    """Events émis correctement."""
    events = []
    for evt in ["prompt_manager_started", "prompt_rendered"]:
        event_bus.on(evt, lambda p, e=evt: events.append(e))
    
    pm = PromptManager(config, event_bus)
    pm.start()
    pm.render("system", tone="test", expertise="test")
    pm.stop()
    
    assert "prompt_manager_started" in events
    assert "prompt_rendered" in events


def test_prompt_manager_custom_prompt(config, event_bus, clean_prompts):
    """Support de prompts custom."""
    # Créer un prompt custom
    custom_file = clean_prompts / "custom.txt"
    custom_file.parent.mkdir(parents=True, exist_ok=True)
    custom_file.write_text("Custom prompt with {{var}}", encoding="utf-8")
    
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Charger prompt custom
    prompt = pm.render("custom", var="value")
    
    assert "Custom prompt with value" == prompt
    
    pm.stop()


def test_prompt_manager_repr(config, event_bus, clean_prompts):
    """__repr__ retourne représentation correcte."""
    pm = PromptManager(config, event_bus)
    
    repr_str = repr(pm)
    assert "PromptManager" in repr_str
    assert "stopped" in repr_str
    
    pm.start()
    repr_str = repr(pm)
    assert "running" in repr_str
    
    pm.stop()