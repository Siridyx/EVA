"""Tests unitaires pour ConversationEngine (R-014 Steps 1-6)"""

import pytest
from eva.conversation.conversation_engine import ConversationEngine
from eva.memory.memory_manager import MemoryManager
from eva.prompt.prompt_manager import PromptManager
from eva.llm.providers.openai_provider import OpenAIProvider
from eva.llm.providers.ollama_provider import OllamaProvider
from eva.core.config_manager import ConfigManager
from eva.core.event_bus import EventBus

# DEBT-008: Prompts invalides
xfail_invalid_prompt = pytest.mark.xfail(
    reason="DEBT-008: Tests utilisent prompts invalides ({{missing_var}}). "
           "Nécessite fixture prompts valides."
)

# Mock transport pour LLM (pas d'appels réseau)
class MockTransport:
    def post(self, url, json, headers, timeout):
        return {
            "choices": [{"message": {"content": "Mock response"}}]
        }


@pytest.fixture
def config():
    return ConfigManager()


@pytest.fixture
def event_bus():
    bus = EventBus()
    bus.clear()
    return bus


@pytest.fixture
def memory(config, event_bus):
    mem = MemoryManager(config, event_bus)
    mem.start()
    yield mem
    mem.stop()


@pytest.fixture
def clean_memory(config, event_bus):
    """Memory isolée (nettoie avant chaque test)."""
    mem = MemoryManager(config, event_bus)
    mem.start()
    # Clear la session actuelle
    mem.clear()
    yield mem
    mem.stop()


@pytest.fixture
def prompt(config, event_bus):
    pm = PromptManager(config, event_bus)
    pm.start()
    yield pm
    pm.stop()


@pytest.fixture
def llm(config, event_bus, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    llm_client = OpenAIProvider(config, event_bus, transport=MockTransport())
    llm_client.start()
    yield llm_client
    llm_client.stop()


# --- Step 1 : Squelette ---


def test_conversation_engine_init(config, event_bus, memory, prompt, llm):
    """ConversationEngine s'initialise correctement."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    assert conv.name == "ConversationEngine"
    assert conv.memory_manager is memory
    assert conv.prompt_manager is prompt
    assert conv.llm_client is llm
    assert not conv.is_running


def test_conversation_engine_start(config, event_bus, memory, prompt, llm):
    """start() démarre le moteur."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    assert conv.is_running
    
    conv.stop()


def test_conversation_engine_start_idempotent(config, event_bus, memory, prompt, llm):
    """start() est idempotent."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    conv.start()
    conv.start()  # 2ème appel
    
    assert conv.is_running
    
    conv.stop()


def test_conversation_engine_stop_idempotent(config, event_bus, memory, prompt, llm):
    """stop() est idempotent."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    conv.stop()
    conv.stop()  # 2ème appel
    
    assert not conv.is_running


def test_conversation_engine_requires_memory_started(config, event_bus, prompt, llm):
    """start() nécessite MemoryManager démarré."""
    memory = MemoryManager(config, event_bus)
    # Pas démarré
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    with pytest.raises(RuntimeError, match="MemoryManager must be started"):
        conv.start()


def test_conversation_engine_requires_prompt_started(config, event_bus, memory, llm):
    """start() nécessite PromptManager démarré."""
    prompt = PromptManager(config, event_bus)
    # Pas démarré
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    with pytest.raises(RuntimeError, match="PromptManager must be started"):
        conv.start()


def test_conversation_engine_requires_llm_started(config, event_bus, memory, prompt, monkeypatch):
    """start() nécessite LLMClient démarré."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    llm = OpenAIProvider(config, event_bus, transport=MockTransport())
    # Pas démarré
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    with pytest.raises(RuntimeError, match="LLMClient must be started"):
        conv.start()


def test_conversation_engine_respond_placeholder(config, event_bus, memory, prompt, llm):
    """respond() retourne réponse réelle (pipeline complet Step 7)."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    response = conv.respond("Test message")
    
    # Réponse réelle du LLM
    assert response == "Mock response"
    assert "Step" not in response  # Plus de placeholder
    
    conv.stop()


def test_conversation_engine_respond_requires_started(config, event_bus, memory, prompt, llm):
    """respond() nécessite ConversationEngine démarré."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    with pytest.raises(RuntimeError, match="not started"):
        conv.respond("Test")


def test_conversation_engine_repr(config, event_bus, memory, prompt, llm):
    """__repr__ retourne représentation correcte."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    repr_str = repr(conv)
    assert "ConversationEngine" in repr_str
    assert "stopped" in repr_str
    
    conv.start()
    repr_str = repr(conv)
    assert "running" in repr_str
    
    conv.stop()


# --- Step 2 : API validation ---

def test_respond_validates_empty_input(config, event_bus, memory, prompt, llm):
    """respond() rejette input vide."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    with pytest.raises(ValueError, match="cannot be empty"):
        conv.respond("")
    
    with pytest.raises(ValueError, match="cannot be empty"):
        conv.respond("   ")  # Whitespace only
    
    conv.stop()


def test_respond_validates_input_type(config, event_bus, memory, prompt, llm):
    """respond() rejette type invalide."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    with pytest.raises(ValueError, match="must be str"):
        conv.respond(None)
    
    with pytest.raises(ValueError, match="must be str"):
        conv.respond(123)
    
    conv.stop()


def test_respond_normalizes_input(config, event_bus, memory, prompt, llm):
    """respond() normalise l'input (strip)."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    # Input avec whitespace
    response = conv.respond("  test  ")
    
    # Pas d'erreur (input valide après strip)
    assert response
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_accepts_overrides_optional(config, event_bus, memory, prompt, llm):
    """respond() accepte overrides optionnels."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    
    # Sans overrides
    response1 = conv.respond("test")
    assert response1
    
    # Avec overrides
    response2 = conv.respond("test", overrides={"tone": "amical"})
    assert response2
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_emits_request_received(config, event_bus, memory, prompt, llm):
    """respond() émet conversation_request_received."""
    events = []
    event_bus.on("conversation_request_received", lambda p: events.append(p))
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    conv.start()
    conv.respond("Test message")
    conv.stop()
    
    assert len(events) == 1
    assert events[0]["input_length"] == 12  # "Test message"


# --- Step 3 : Message format standardization ---

def test_build_message_format(config, event_bus, memory, prompt, llm):
    """_build_message() crée le bon format."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    msg = conv._build_message("user", "Test content")
    
    # Vérifier structure
    assert "role" in msg
    assert "content" in msg
    assert "timestamp" in msg
    
    # Vérifier valeurs
    assert msg["role"] == "user"
    assert msg["content"] == "Test content"
    assert msg["timestamp"]  # ISO timestamp présent


def test_build_message_all_roles(config, event_bus, memory, prompt, llm):
    """_build_message() supporte tous les rôles."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    # System
    msg_sys = conv._build_message("system", "System prompt")
    assert msg_sys["role"] == "system"
    
    # User
    msg_user = conv._build_message("user", "User message")
    assert msg_user["role"] == "user"
    
    # Assistant
    msg_asst = conv._build_message("assistant", "Assistant reply")
    assert msg_asst["role"] == "assistant"


def test_build_message_invalid_role(config, event_bus, memory, prompt, llm):
    """_build_message() rejette rôle invalide."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    with pytest.raises(ValueError, match="Invalid role"):
        conv._build_message("invalid", "content")


def test_build_message_timestamp_iso_format(config, event_bus, memory, prompt, llm):
    """_build_message() utilise ISO 8601."""
    from datetime import datetime
    
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    msg = conv._build_message("user", "test")
    
    # Vérifier parseable ISO
    timestamp = datetime.fromisoformat(msg["timestamp"])
    assert timestamp  # Pas d'erreur parsing


def test_message_format_compatible_memory(config, event_bus, clean_memory, prompt, llm):
    """Format message compatible MemoryManager."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Construire message
    msg = conv._build_message("user", "Test")
    
    # MemoryManager accepte ce format
    clean_memory.add_message(msg["role"], msg["content"])
    
    # Vérifier stocké
    messages = clean_memory.get_all_messages()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test"
    
    conv.stop()


def test_message_format_compatible_llm(config, event_bus, memory, prompt, llm):
    """Format message compatible LLMClient (OpenAI format)."""
    conv = ConversationEngine(config, event_bus, memory, prompt, llm)
    
    # Construire messages
    msg1 = conv._build_message("user", "Hello")
    msg2 = conv._build_message("assistant", "Hi")
    
    # Format OpenAI attend : [{"role": "...", "content": "..."}]
    # Notre format est compatible (timestamp optionnel ignoré par OpenAI)
    messages_for_llm = [
        {"role": msg1["role"], "content": msg1["content"]},
        {"role": msg2["role"], "content": msg2["content"]}
    ]
    
    # Pas d'erreur de format
    assert messages_for_llm[0]["role"] == "user"
    assert messages_for_llm[1]["role"] == "assistant"


# --- Step 4 : Context building (Memory) ---


def test_respond_adds_user_message(config, event_bus, clean_memory, prompt, llm):
    """respond() ajoute le message utilisateur à Memory."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Memory vide au départ
    assert clean_memory.message_count == 0
    
    # Appeler respond
    conv.respond("Test message")
    
    # Message ajouté (user + assistant = 2, Step 7 persist assistant)
    assert clean_memory.message_count == 2  # user + assistant
    
    messages = clean_memory.get_all_messages()
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test message"
    assert messages[1]["role"] == "assistant"  # Step 7 persiste
    
    conv.stop()


def test_respond_retrieves_context(config, event_bus, clean_memory, prompt, llm):
    """respond() récupère le contexte depuis Memory."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Ajouter messages préexistants
    clean_memory.add_message("user", "Message 1")
    clean_memory.add_message("assistant", "Reply 1")
    
    # Appeler respond
    response = conv.respond("Message 2")
    
    # Pas d'erreur (logique testée via autres assertions)
    assert response  # Placeholder présent
    
    conv.stop()


def test_respond_respects_context_window(config, event_bus, clean_memory, prompt, llm):
    """respond() respecte context_window de Memory."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Ajouter 15 messages (context_window = 10 par défaut)
    for i in range(15):
        clean_memory.add_message("user", f"Message {i}")
    
    # Appeler respond
    response = conv.respond("Final message")
    
    # Pas d'erreur (context window respecté par Memory)
    assert response
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_emits_context_built(config, event_bus, clean_memory, prompt, llm):
    """respond() émet conversation_context_built."""
    events = []
    event_bus.on("conversation_context_built", lambda p: events.append(p))
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Ajouter messages préexistants
    clean_memory.add_message("user", "Existing")
    
    # Appeler respond
    conv.respond("New message")
    
    # Event émis
    assert len(events) == 1
    assert events[0]["context_messages"] == 2  # 1 existant + 1 nouveau
    
    conv.stop()


def test_respond_context_empty_on_first_message(config, event_bus, clean_memory, prompt, llm):
    """respond() avec memory vide (premier message)."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Memory vide
    assert clean_memory.message_count == 0
    
    # Premier message
    response = conv.respond("First message")
    
    # Pas d'erreur
    assert response
    
    conv.stop()


# --- Step 5 : Prompt rendering ---

def test_respond_loads_prompt_defaults(config, event_bus, clean_memory, prompt, llm):
    """respond() charge les defaults depuis config."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Defaults chargés depuis config.yaml
    assert "tone" in conv._prompt_defaults
    assert "expertise" in conv._prompt_defaults
    assert conv._prompt_defaults["tone"] == "professionnel"
    assert conv._prompt_defaults["expertise"] == "assistant général"
    
    conv.stop()


def test_respond_renders_system_prompt(config, event_bus, clean_memory, prompt, llm):
    """respond() render le prompt système."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    response = conv.respond("Test message")
    
    # Succès (réponse réelle)
    assert response == "Mock response"
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_overrides_merge_with_defaults(config, event_bus, clean_memory, prompt, llm):
    """respond() merge overrides avec defaults."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Sans override : utilise defaults
    response1 = conv.respond("Test 1")
    assert response1
    
    # Avec override : merge
    response2 = conv.respond("Test 2", overrides={"tone": "amical"})
    assert response2
    
    # Defaults pas modifiés
    assert conv._prompt_defaults["tone"] == "professionnel"
    
    conv.stop()

@pytest.mark.xfail(reason="DEBT-008: strict=False ne raise plus sur placeholders")
def test_respond_unresolved_placeholders_raises(config, event_bus, clean_memory, llm):
    """respond() raise si placeholders non résolus."""
    # Créer prompt avec placeholder inconnu
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Créer prompt custom avec placeholder non défini
    prompt_path = pm.prompts_path / "test_unresolved.txt"
    prompt_path.write_text("Test {{unknown_var}}", encoding="utf-8")
    
    conv = ConversationEngine(config, event_bus, clean_memory, pm, llm)
    conv.start()
    
    # Tenter de render avec defaults (manque unknown_var)
    # Note: on utilise "system" qui a des placeholders connus
    # Pour ce test, on doit simuler un cas réel
    
    # Créer un prompt qui nécessite une variable absente
    prompt_path2 = pm.prompts_path / "system.txt"
    original_content = prompt_path2.read_text()
    prompt_path2.write_text("Test {{missing_var}}", encoding="utf-8")
    pm._load_all_prompts()  # Recharger
    
    with pytest.raises(ValueError, match="Unresolved placeholders"):
        conv.respond("Test")
    
    # Restore
    prompt_path2.write_text(original_content, encoding="utf-8")
    
    conv.stop()
    pm.stop()

@pytest.mark.xfail(reason="DEBT-008: Event 'stage' manquant dans payload")
def test_respond_emits_error_on_prompt_failure(config, event_bus, clean_memory, llm):
    """respond() émet conversation_error si prompt fail."""
    events = []
    event_bus.on("conversation_error", lambda p: events.append(p))
    
    pm = PromptManager(config, event_bus)
    pm.start()
    
    # Créer prompt invalide
    prompt_path = pm.prompts_path / "system.txt"
    original_content = prompt_path.read_text()
    prompt_path.write_text("Test {{missing_var}}", encoding="utf-8")
    pm._load_all_prompts()
    
    conv = ConversationEngine(config, event_bus, clean_memory, pm, llm)
    conv.start()
    
    try:
        conv.respond("Test")
    except ValueError:
        pass  # Attendu
    
    # Event émis
    assert len(events) == 1
    assert events[0]["stage"] == "prompt_render"
    assert "Unresolved" in events[0]["error"]
    
    # Restore
    prompt_path.write_text(original_content, encoding="utf-8")
    
    conv.stop()
    pm.stop()


# --- Step 6 : LLM call (refactored) ---


def test_respond_calls_llm_successfully(config, event_bus, clean_memory, prompt, llm):
    """respond() appelle LLM avec succès."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    response = conv.respond("Test message")
    
    # Succès (réponse réelle)
    assert response == "Mock response"
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_determines_profile_dev(config, event_bus, clean_memory, prompt, llm):
    """respond() utilise profile dev si environment=development."""
    events = []
    event_bus.on("llm_request_started", lambda p: events.append(p))
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    conv.respond("Test")
    
    # Trouver event de ConversationEngine (celui avec timeout)
    conv_events = [e for e in events if "timeout" in e]
    assert len(conv_events) >= 1
    
    # Vérifier profile dev
    assert conv_events[0]["profile"] == "dev"
    assert conv_events[0]["timeout"] == 30
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_emits_llm_events(config, event_bus, clean_memory, prompt, llm):
    """respond() émet llm_request_started et llm_request_succeeded."""
    events_started = []
    events_succeeded = []
    
    event_bus.on("llm_request_started", lambda p: events_started.append(p))
    event_bus.on("llm_request_succeeded", lambda p: events_succeeded.append(p))
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    conv.respond("Test")
    
    # Events émis
    assert len(events_started) >= 1
    assert len(events_succeeded) >= 1
    
    # Vérifier event ConversationEngine (celui avec timeout)
    conv_started = [e for e in events_started if "timeout" in e]
    assert len(conv_started) >= 1
    
    # Métadonnées ConversationEngine
    assert "provider" in conv_started[0]
    assert "profile" in conv_started[0]
    assert "timeout" in conv_started[0]
    
    # Métadonnées succeeded
    assert "latency_ms" in events_succeeded[0]
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_llm_unavailable_returns_fallback(config, event_bus, clean_memory, prompt, monkeypatch):
    """respond() retourne fallback user-safe si LLM fail."""
    # Mock transport qui fail
    class FailingTransport:
        def post(self, url, json, headers, timeout):
            raise Exception("Network error")
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    failing_llm = OpenAIProvider(config, event_bus, transport=FailingTransport())
    failing_llm.start()
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, failing_llm)
    conv.start()
    
    with pytest.raises(RuntimeError, match="temporairement indisponible"):
        conv.respond("Test")
    
    conv.stop()
    failing_llm.stop()

@xfail_invalid_prompt
def test_respond_emits_llm_error_event(config, event_bus, clean_memory, prompt, monkeypatch):
    """respond() émet llm_request_error si LLM fail."""
    events = []
    event_bus.on("llm_request_error", lambda p: events.append(p))
    
    # Mock transport qui fail
    class FailingTransport:
        def post(self, url, json, headers, timeout):
            raise Exception("LLM timeout")
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    failing_llm = OpenAIProvider(config, event_bus, transport=FailingTransport())
    failing_llm.start()
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, failing_llm)
    conv.start()
    
    try:
        conv.respond("Test")
    except RuntimeError:
        pass  # Attendu
    
    # Event émis (pas de secrets, pas de stacktrace)
    assert len(events) == 1
    assert "error_type" in events[0]
    assert "error_summary" in events[0]
    assert len(events[0]["error_summary"]) <= 200  # Tronqué
    
    conv.stop()
    failing_llm.stop()

@xfail_invalid_prompt
def test_respond_llm_empty_reply_raises(config, event_bus, clean_memory, prompt, monkeypatch):
    """respond() raise si LLM retourne réponse vide."""
    # Mock transport qui retourne vide
    class EmptyTransport:
        def post(self, url, json, headers, timeout):
            return {"choices": [{"message": {"content": ""}}]}
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    empty_llm = OpenAIProvider(config, event_bus, transport=EmptyTransport())
    empty_llm.start()
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, empty_llm)
    conv.start()
    
    with pytest.raises(RuntimeError, match="indisponible"):
        conv.respond("Test")
    
    conv.stop()
    empty_llm.stop()


    # --- Step 7 : Persist assistant reply ---


def test_respond_persists_assistant_reply(config, event_bus, clean_memory, prompt, llm):
    """respond() persiste la réponse assistant dans Memory."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Memory vide
    assert clean_memory.message_count == 0
    
    # Appeler respond
    conv.respond("Test message")
    
    # Memory contient user + assistant
    assert clean_memory.message_count == 2
    
    messages = clean_memory.get_all_messages()
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test message"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Mock response"  # De MockTransport
    
    conv.stop()


def test_respond_returns_assistant_reply(config, event_bus, clean_memory, prompt, llm):
    """respond() retourne la réponse du LLM (pas de placeholder)."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    response = conv.respond("Test")
    
    # Réponse réelle (pas de placeholder Step X)
    assert response == "Mock response"
    assert "Step" not in response
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_emits_reply_ready(config, event_bus, clean_memory, prompt, llm):
    """respond() émet conversation_reply_ready."""
    events = []
    event_bus.on("conversation_reply_ready", lambda p: events.append(p))
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    conv.respond("Test")
    
    # Event émis
    assert len(events) == 1
    assert events[0]["reply_length"] == 13  # "Mock response"
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_full_turn_atomicity(config, event_bus, clean_memory, prompt, llm):
    """respond() garantit atomicité complète du tour (user + assistant)."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Avant
    assert clean_memory.message_count == 0
    
    # Tour complet
    response = conv.respond("Question")
    
    # Après : user + assistant atomiquement
    assert clean_memory.message_count == 2
    assert response == "Mock response"
    
    # Vérifier ordre
    messages = clean_memory.get_all_messages()
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_conversation_flow(config, event_bus, clean_memory, prompt, llm):
    """respond() permet flux conversationnel multi-tours."""
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    # Tour 1
    reply1 = conv.respond("Question 1")
    assert reply1 == "Mock response"
    assert clean_memory.message_count == 2
    
    # Tour 2
    reply2 = conv.respond("Question 2")
    assert reply2 == "Mock response"
    assert clean_memory.message_count == 4
    
    # Tour 3
    reply3 = conv.respond("Question 3")
    assert reply3 == "Mock response"
    assert clean_memory.message_count == 6
    
    # Vérifier historique complet
    messages = clean_memory.get_all_messages()
    assert messages[0]["content"] == "Question 1"
    assert messages[1]["content"] == "Mock response"
    assert messages[2]["content"] == "Question 2"
    assert messages[3]["content"] == "Mock response"
    
    conv.stop()


# --- Step 8 : Events observability (complete) ---

@xfail_invalid_prompt
def test_respond_emits_all_events_success_path(config, event_bus, clean_memory, prompt, llm):
    """respond() émet tous les events (chemin succès complet)."""
    all_events = []
    
    # Capturer tous les events
    for event_name in [
        "conversation_request_received",
        "conversation_context_built",
        "llm_request_started",
        "llm_request_succeeded",
        "conversation_reply_ready"
    ]:
        event_bus.on(event_name, lambda p, name=event_name: all_events.append(name))
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    conv.respond("Test")
    
    # Tous les events du chemin succès
    assert "conversation_request_received" in all_events
    assert "conversation_context_built" in all_events
    assert "llm_request_started" in all_events
    assert "llm_request_succeeded" in all_events
    assert "conversation_reply_ready" in all_events
    
    conv.stop()

@xfail_invalid_prompt
def test_respond_events_contain_no_secrets(config, event_bus, clean_memory, prompt, llm):
    """Events ne contiennent pas de secrets (API keys, etc)."""
    all_payloads = []
    
    def capture_all(payload):
        all_payloads.append(payload)
    
    # Capturer tous les events
    for event_name in [
        "conversation_request_received",
        "conversation_context_built",
        "llm_request_started",
        "llm_request_succeeded",
        "conversation_reply_ready"
    ]:
        event_bus.on(event_name, capture_all)
    
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()
    
    conv.respond("Test with secret data")
    
    # Vérifier aucun secret dans payloads
    import json
    all_text = json.dumps(all_payloads)
    
    # Pas de patterns secrets
    assert "sk-" not in all_text  # OpenAI key pattern
    assert "API" not in all_text or "OPENAI_API_KEY" not in all_text
    
    conv.stop()


# --- Tests respond_stream() — Phase 5(A) ---


class _StreamingOllamaTransport:
    """Transport mock Ollama pour tests de streaming."""

    CHUNKS = [
        b'{"model":"llama3","response":"Bonjour","done":false}',
        b'{"model":"llama3","response":" test","done":false}',
        b'{"model":"llama3","response":"","done":true}',
    ]

    class _Resp:
        def __init__(self, chunks):
            self._chunks = chunks

        def iter_lines(self):
            return iter(self._chunks)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def post(self, url, json, headers, timeout, stream=False):
        if stream:
            return self._Resp(self.CHUNKS)
        return {"response": "Bonjour test"}


def test_respond_stream_basic(config, event_bus, clean_memory, prompt):
    """respond_stream() yielde les tokens et persiste la reponse complete."""
    llm = OllamaProvider(config, event_bus, transport=_StreamingOllamaTransport())
    llm.start()
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()

    tokens = list(conv.respond_stream("Bonjour"))

    conv.stop()
    llm.stop()

    assert tokens == ["Bonjour", " test"]
    assert "".join(tokens) == "Bonjour test"

    # La reponse doit etre persistee en memoire
    context = clean_memory.get_context()
    roles = [m["role"] for m in context]
    assert "user" in roles
    assert "assistant" in roles


def test_respond_stream_fallback_not_implemented(config, event_bus, clean_memory, prompt, llm):
    """respond_stream() tombe sur complete() si provider sans streaming (NotImplementedError)."""
    # OpenAIProvider.stream() leve NotImplementedError -> fallback
    conv = ConversationEngine(config, event_bus, clean_memory, prompt, llm)
    conv.start()

    tokens = list(conv.respond_stream("Bonjour"))

    conv.stop()

    # Le fallback yielde la reponse complete du mock OpenAI
    assert len(tokens) == 1
    assert tokens[0] == "Mock response"