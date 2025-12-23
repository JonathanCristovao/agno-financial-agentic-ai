"""
Finance Assistant - Assistente Financeiro com IA
Arquitetura limpa e modular com suporte multilíngue
"""
import re
from datetime import datetime
from typing import List, Dict, Optional

import streamlit as st
import yfinance as yf
import pandas as pd
from openai import OpenAI
from duckduckgo_search import DDGS


# =========================
# Traduções
# =========================
TRANSLATIONS = {
    "pt": {
        "page_title": "Assistente Financeiro",
        "page_caption": "Assistente financeiro inteligente com análise de mercado",
        "config_header": "⚙️ Configuração",
        "language": "Idioma",
        "api_key": "OpenAI API Key",
        "api_key_help": "Sua chave de API da OpenAI",
        "model": "Modelo",
        "clear_history": "🧹 Limpar Histórico",
        "chat_tab": "💬 Chat",
        "analysis_tab": "📊 Análise de Ativo",
        "chat_placeholder": "Ex: Como está o preço de AAPL e qual a perspectiva?",
        "configure_api": "⚠️ Configure sua API key no menu lateral",
        "analyzing": "Analisando...",
        "current_prices": "**Preços Atuais:**",
        "recent_news": "**Notícias Recentes:**",
        "detailed_analysis": "📊 Análise Detalhada de Ativo",
        "ticker_label": "Ticker do ativo:",
        "start_date": "Data inicial",
        "end_date": "Data final",
        "load_data": "📈 Carregar Dados",
        "loading_data": "Carregando dados...",
        "data_loaded": "✅ Dados carregados: {count} registros",
        "error_loading": "❌ Não foi possível obter dados para este ticker e período",
        "last_close": "Último Fechamento",
        "period_change": "Variação Período",
        "maximum": "Máxima",
        "minimum": "Mínima",
        "view_recent": "📋 Ver dados recentes",
        "ask_question": "Faça uma pergunta sobre o ativo:",
        "question_placeholder": "Ex: Qual a tendência do preço? Vale a pena investir?",
        "analyze_button": "🧠 Analisar",
        "analyzing_ai": "Analisando com IA...",
        "answer": "### Resposta:",
        "error": "Erro: {error}",
        "system_prompt": """Você é Arash+, um assistente financeiro especializado.
Data atual: {date}.
Seja direto, técnico e baseie suas respostas nos dados fornecidos.
Sempre cite as fontes quando usar informações externas.
Responda em português.""",
        "data_context": """**Dados do ativo {ticker}:**
- Período: {start} até {end}
- Preço atual: ${price:.2f}
- Variação: {change:.2f}%
- Média: ${mean:.2f}
- Volatilidade (std): ${std:.2f}

Últimos 5 dias:
{recent}"""
    },
    "en": {
        "page_title": "Finance Assistant",
        "page_caption": "Intelligent financial assistant with market analysis",
        "config_header": "⚙️ Settings",
        "language": "Language",
        "api_key": "OpenAI API Key",
        "api_key_help": "Your OpenAI API key",
        "model": "Model",
        "clear_history": "🧹 Clear History",
        "chat_tab": "💬 Chat",
        "analysis_tab": "📊 Asset Analysis",
        "chat_placeholder": "Ex: What's the price of AAPL and what's the outlook?",
        "configure_api": "⚠️ Configure your API key in the sidebar",
        "analyzing": "Analyzing...",
        "current_prices": "**Current Prices:**",
        "recent_news": "**Recent News:**",
        "detailed_analysis": "📊 Detailed Asset Analysis",
        "ticker_label": "Asset ticker:",
        "start_date": "Start date",
        "end_date": "End date",
        "load_data": "📈 Load Data",
        "loading_data": "Loading data...",
        "data_loaded": "✅ Data loaded: {count} records",
        "error_loading": "❌ Unable to fetch data for this ticker and period",
        "last_close": "Last Close",
        "period_change": "Period Change",
        "maximum": "Maximum",
        "minimum": "Minimum",
        "view_recent": "📋 View recent data",
        "ask_question": "Ask a question about the asset:",
        "question_placeholder": "Ex: What's the price trend? Is it worth investing?",
        "analyze_button": "🧠 Analyze",
        "analyzing_ai": "Analyzing with AI...",
        "answer": "### Answer:",
        "error": "Error: {error}",
        "system_prompt": """You are Arash+, a specialized financial assistant.
Current date: {date}.
Be direct, technical and base your answers on the provided data.
Always cite sources when using external information.
Respond in English.""",
        "data_context": """**Asset data for {ticker}:**
- Period: {start} to {end}
- Current price: ${price:.2f}
- Change: {change:.2f}%
- Average: ${mean:.2f}
- Volatility (std): ${std:.2f}

Last 5 days:
{recent}"""
    }
}


def get_text(key: str) -> str:
    """Retorna texto traduzido baseado no idioma selecionado"""
    lang = st.session_state.get("language", "pt")
    return TRANSLATIONS[lang].get(key, key)


# =========================
# Configuração
# =========================
st.set_page_config(
    page_title="Finance Assistant",
    page_icon="💰",
    layout="wide"
)


# =========================
# Serviços de Dados
# =========================
class DataService:
    """Serviço responsável por buscar dados financeiros e notícias"""
    
    @staticmethod
    @st.cache_data(ttl=60)
    def get_stock_data(ticker: str) -> Optional[Dict]:
        """Obtém dados de preço do ticker usando yfinance"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            
            if hist.empty:
                return None
            
            info = stock.info
            last_price = hist['Close'].iloc[-1]
            
            return {
                "ticker": ticker,
                "price": last_price,
                "currency": info.get("currency", "USD"),
                "name": info.get("shortName", ticker)
            }
        except Exception as e:
            st.warning(f"{get_text('error').format(error=str(e))}")
            return None
    
    @staticmethod
    def get_historical_data(ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Obtém dados históricos do ticker"""
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval="1d",
                progress=False
            )
            
            if df.empty:
                return None
            
            # Normaliza colunas MultiIndex se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            return df
        except Exception as e:
            st.error(f"{get_text('error').format(error=str(e))}")
            return None
    
    @staticmethod
    def search_news(query: str, max_results: int = 5) -> List[Dict]:
        """Busca notícias usando DuckDuckGo"""
        results = []
        try:
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "link": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
        except Exception as e:
            st.warning(f"{get_text('error').format(error=str(e))}")
        
        return results


# =========================
# Processamento de Texto
# =========================
class TextProcessor:
    """Processa texto para extrair tickers e preparar contexto"""
    
    STOP_WORDS = {
        "AND", "OR", "THE", "NEWS", "STOCK", "PRICE", "TODAY", "WITH", "ABOUT",
        "WHAT", "TELL", "ME", "QUE", "PODE", "DISSE", "DA", "DE", "DO", "DAS",
        "DOS", "EM", "NO", "NA", "NOS", "NAS", "UM", "UMA", "PARA", "POR", "COM",
        "ACOES", "AÇÃO", "ATIVO", "ATIVOS", "EMPRESA", "PRECO", "PREÇO", "HOJE"
    }
    
    @classmethod
    def extract_tickers(cls, text: str) -> List[str]:
        """Extrai tickers do texto"""
        text = text.upper().strip()
        
        # Padrões explícitos: $AAPL, BTC-USD, AAPL.SA, ^GSPC
        explicit_pattern = r"(?:\$\s*)?(\^?[A-Z]{1,6}(?:[.-][A-Z]{1,6})?)"
        explicit_tickers = re.findall(explicit_pattern, text)
        
        # Palavras simples (2-5 letras maiúsculas)
        simple_pattern = r"\b[A-Z]{2,5}\b"
        simple_tickers = re.findall(simple_pattern, text)
        
        # Filtra stopwords e valida
        candidates = []
        for ticker in explicit_tickers + simple_tickers:
            ticker = ticker.replace("$", "").strip()
            
            if ticker in cls.STOP_WORDS:
                continue
            
            # Heurística: aceita se parece ticker
            looks_valid = (
                ticker.startswith("^") or
                "-" in ticker or
                "." in ticker or
                (2 <= len(ticker) <= 5)
            )
            
            if looks_valid:
                candidates.append(ticker)
        
        # Remove duplicatas mantendo ordem
        return list(dict.fromkeys(candidates))[:5]


# =========================
# Serviço de IA
# =========================
class AIService:
    """Serviço de comunicação com OpenAI"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        if not api_key:
            raise ValueError("API key é obrigatória")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = get_text("system_prompt").format(
            date=datetime.now().strftime('%Y-%m-%d')
        )
    
    def generate_response(self, user_prompt: str, context: str = "") -> str:
        """Gera resposta usando OpenAI"""
        try:
            full_prompt = f"{context}\n\n{user_prompt}" if context else user_prompt
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"{get_text('error').format(error=str(e))}"


# =========================
# Interface - Sidebar
# =========================
def render_sidebar() -> Dict:
    """Renderiza a sidebar e retorna configurações"""
    with st.sidebar:
        st.header(get_text("config_header"))
        
        # Seletor de idioma
        if "language" not in st.session_state:
            st.session_state.language = "pt"
        
        lang_options = {"Português": "pt", "English": "en"}
        selected_lang = st.selectbox(
            get_text("language"),
            options=list(lang_options.keys()),
            index=0 if st.session_state.language == "pt" else 1
        )
        
        # Atualiza idioma se mudou
        new_lang = lang_options[selected_lang]
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
        
        st.divider()
        
        api_key = st.text_input(
            get_text("api_key"),
            type="password",
            help=get_text("api_key_help")
        )
        
        model = st.selectbox(
            get_text("model"),
            [
            "gpt-5.2",
            "gpt-5.2 pro",
            "gpt-5.1",
            "gpt-5",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-5-mini",
            "gpt-5 nano",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4-mini"],
            index=0
        )
        
        st.divider()
        
        if st.button(get_text("clear_history"), use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        return {"api_key": api_key, "model": model}


# =========================
# Interface - Chat
# =========================
def render_chat_tab(config: Dict):
    """Renderiza a aba de chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostra histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input do usuário
    if prompt := st.chat_input(get_text("chat_placeholder")):
        # Valida API key
        if not config.get("api_key"):
            st.error(get_text("configure_api"))
            return
        
        # Adiciona mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Processa resposta
        with st.chat_message("assistant"):
            with st.spinner(get_text("analyzing")):
                # Extrai tickers e busca dados
                tickers = TextProcessor.extract_tickers(prompt)
                context_parts = []
                
                # Dados de preços
                if tickers:
                    prices = []
                    for ticker in tickers:
                        data = DataService.get_stock_data(ticker)
                        if data and data.get("price"):
                            prices.append(
                                f"- {data['ticker']} ({data['name']}): "
                                f"{data['price']:.2f} {data['currency']}"
                            )
                    
                    if prices:
                        context_parts.append(get_text("current_prices") + "\n" + "\n".join(prices))
                
                # Notícias relevantes
                news = DataService.search_news(prompt)
                if news:
                    news_text = "\n".join([
                        f"- [{n['title']}]({n['link']})"
                        for n in news[:3]
                    ])
                    context_parts.append(f"{get_text('recent_news')}\n{news_text}")
                
                # Gera resposta
                context = "\n\n".join(context_parts) if context_parts else ""
                
                try:
                    ai_service = AIService(config["api_key"], config["model"])
                    answer = ai_service.generate_response(prompt, context)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(get_text("error").format(error=str(e)))


# =========================
# Interface - Análise
# =========================
def render_analysis_tab(config: Dict):
    """Renderiza a aba de análise de ativos"""
    st.subheader(get_text("detailed_analysis"))
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        ticker = st.text_input(get_text("ticker_label"), value="AAPL")
    
    with col2:
        start_date = st.date_input(get_text("start_date"), value=datetime(2023, 1, 1))
    
    with col3:
        end_date = st.date_input(get_text("end_date"), value=datetime.now())
    
    # Botão para carregar dados
    if st.button(get_text("load_data"), type="primary", use_container_width=True):
        with st.spinner(get_text("loading_data")):
            df = DataService.get_historical_data(ticker, str(start_date), str(end_date))
            
            if df is not None and not df.empty:
                st.session_state.analysis_df = df
                st.session_state.analysis_ticker = ticker
                st.session_state.analysis_start = start_date
                st.session_state.analysis_end = end_date
                st.success(get_text("data_loaded").format(count=len(df)))
            else:
                st.error(get_text("error_loading"))
    
    # Mostra dados se já carregados
    if "analysis_df" in st.session_state:
        df = st.session_state.analysis_df
        ticker = st.session_state.analysis_ticker
        
        # Estatísticas básicas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(get_text("last_close"), f"${df['Close'].iloc[-1]:.2f}")
        with col2:
            change = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100)
            st.metric(get_text("period_change"), f"{change:.2f}%")
        with col3:
            st.metric(get_text("maximum"), f"${df['High'].max():.2f}")
        with col4:
            st.metric(get_text("minimum"), f"${df['Low'].min():.2f}")
        
        # Gráfico usando Plotly via plots.py
        try:
            from plots import StockChart
            chart = StockChart(df, title=f"{ticker} - {get_text('detailed_analysis')}")
            chart.add_price_chart()
            chart.add_volume_chart()
            chart.render_chart()
        except Exception as e:
            st.error(get_text("error").format(error=str(e)))
        
        # Dados recentes
        with st.expander(get_text("view_recent")):
            st.dataframe(df.tail(20), use_container_width=True)
        
        st.divider()
        
        # Análise com IA
        col1, col2 = st.columns([3, 1])
        with col1:
            question = st.text_input(
                get_text("ask_question"),
                placeholder=get_text("question_placeholder")
            )
        with col2:
            analyze = st.button(get_text("analyze_button"), use_container_width=True)
        
        if analyze and question:
            if not config.get("api_key"):
                st.error(get_text("configure_api"))
            else:
                with st.spinner(get_text("analyzing_ai")):
                    # Prepara contexto com dados
                    context = get_text("data_context").format(
                        ticker=ticker,
                        start=st.session_state.analysis_start,
                        end=st.session_state.analysis_end,
                        price=df['Close'].iloc[-1],
                        change=change,
                        mean=df['Close'].mean(),
                        std=df['Close'].std(),
                        recent=df[['Open', 'High', 'Low', 'Close', 'Volume']].tail().to_string()
                    )
                    
                    try:
                        ai_service = AIService(config["api_key"], config["model"])
                        answer = ai_service.generate_response(question, context)
                        st.markdown(get_text("answer"))
                        st.markdown(answer)
                    except Exception as e:
                        st.error(get_text("error").format(error=str(e)))


# =========================
# Main
# =========================
def main():
    # Inicializa idioma se não existir
    if "language" not in st.session_state:
        st.session_state.language = "pt"
    
    st.title(f"💰 {get_text('page_title')}")
    st.caption(get_text("page_caption"))
    
    # Configurações
    config = render_sidebar()
    
    # Tabs
    tab1, tab2 = st.tabs([get_text("chat_tab"), get_text("analysis_tab")])
    
    with tab1:
        render_chat_tab(config)
    
    with tab2:
        render_analysis_tab(config)


if __name__ == "__main__":
    main()