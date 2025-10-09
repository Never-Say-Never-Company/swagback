# nsnapp/ai_service.py

from google import genai
from google.genai.errors import APIError
from decouple import config
import json

# Dicionário simples para armazenar sessões de chat em memória. 
# ATENÇÃO: Em produção, isto deve ser substituído por um cache como Redis 
# para persistir o histórico entre requisições ou workers.
CHAT_SESSIONS = {}

# Configuração e Inicialização do Cliente Gemini
GEMINI_API_KEY = config("GEMINI_API_KEY", default=None) 

gemini_client = None
try:
    if GEMINI_API_KEY:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    # Apenas um aviso, o endpoint irá retornar 503 se o cliente for None
    print(f"Aviso: Erro ao inicializar o cliente Gemini. O chat pode falhar. Erro: {e}")
    

def get_or_create_chat_session(session_id: str, system_instruction: str) -> genai.chats.Chat | None:
    """
    Obtém uma sessão de chat existente ou cria uma nova com uma System Instruction específica.
    
    CORREÇÃO DE TIPAGEM: genai.Chat foi corrigido para genai.chats.Chat.
    """
    if gemini_client is None:
        return None

    if session_id not in CHAT_SESSIONS:
        # Cria uma nova sessão de chat com a instrução de sistema
        chat = gemini_client.chats.create(
            model='gemini-2.5-flash',
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024 # Garante espaço para respostas consultivas
            )
        )
        CHAT_SESSIONS[session_id] = chat
        return chat
        
    return CHAT_SESSIONS[session_id]


def send_message_to_chat(session_id: str, message: str) -> str | None:
    """
    Envia uma mensagem para a sessão de chat, mantendo o histórico.
    """
    # 1. Definição do Comportamento (System Instruction)
    system_instruction = (
        "Você é um assistente de gestão de projetos consultivo e especialista em "
        "metodologias ágeis. Sua função é analisar dados de projetos e manter uma "
        "conversa produtiva com o usuário, respondendo a perguntas e oferecendo "
        "sugestões com base no histórico da conversa. O tom é profissional, direto e de suporte. "
        "Responda em Português do Brasil."
    )
    
    chat = get_or_create_chat_session(session_id, system_instruction)

    if chat is None:
        return None # Cliente Gemini não inicializado ou falha na criação da sessão

    try:
        # Envia a mensagem e obtém a resposta. A sessão gerencia o histórico.
        response = chat.send_message(message)
        
        feedback_text = response.text
        
        if not feedback_text:
            # Tenta logar o motivo do bloqueio para debug
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback and response.prompt_feedback.block_reason else 'Desconhecido'
            print(f"Gemini Chat falhou em gerar conteúdo. Motivo: {block_reason}")
            return None 

        return feedback_text
        
    except APIError as e:
        print(f"Erro na API Gemini: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao enviar mensagem de chat: {e}")
        return None

def reset_chat_session(session_id: str) -> bool:
    """
    Remove uma sessão de chat do armazenamento, resetando a conversa.
    """
    if session_id in CHAT_SESSIONS:
        del CHAT_SESSIONS[session_id]
        return True
    return False

# Nota: As demais funções de feedback de IA foram removidas deste arquivo para simplicidade e foco no chat.