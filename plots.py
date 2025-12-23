"""
Módulo de visualização de dados financeiros
Gráficos interativos com Plotly
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza DataFrame do yfinance para formato padrão OHLCV
    Lida com MultiIndex e diferentes formatos de colunas
    """
    df = df.copy()
    
    # Converte Date para index se necessário
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    
    # Garante que index seja DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    
    # Lida com MultiIndex (comum quando baixa múltiplos tickers)
    if isinstance(df.columns, pd.MultiIndex):
        # Pega o primeiro ticker disponível
        tickers = df.columns.get_level_values(0).unique()
        if len(tickers) > 0:
            df = df[tickers[0]]
    
    # Normaliza nomes das colunas
    column_mapping = {
        col: col.strip().title() 
        for col in df.columns 
        if isinstance(col, str)
    }
    
    # Mapeamento específico para colunas conhecidas
    specific_mapping = {
        'adj close': 'Adj Close',
        'adjclose': 'Adj Close',
        'adjusted close': 'Adj Close'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name.lower() in specific_mapping:
            column_mapping[old_name] = specific_mapping[old_name.lower()]
    
    df = df.rename(columns=column_mapping)
    
    return df


@dataclass
class StockChart:
    """
    Classe para criar gráficos financeiros interativos
    
    Attributes:
        df: DataFrame com dados OHLCV
        title: Título do gráfico
        height: Altura em pixels
        show_range_slider: Mostrar slider de range
    """
    df: pd.DataFrame
    title: Optional[str] = None
    height: int = 700
    show_range_slider: bool = False
    
    def __post_init__(self):
        """Valida e normaliza os dados"""
        if self.df is None or self.df.empty:
            raise ValueError("DataFrame vazio fornecido")
        
        # Normaliza o DataFrame
        self.df = normalize_dataframe(self.df)
        
        # Valida colunas necessárias
        required_cols = ["Open", "High", "Low", "Close"]
        missing = [col for col in required_cols if col not in self.df.columns]
        
        if missing:
            available = list(self.df.columns)
            raise ValueError(
                f"Colunas obrigatórias ausentes: {missing}. "
                f"Colunas disponíveis: {available}"
            )
        
        self._show_price = False
        self._show_volume = False
    
    def add_price_chart(self):
        """Adiciona gráfico de preços (candlestick)"""
        self._show_price = True
        return self
    
    def add_volume_chart(self):
        """Adiciona gráfico de volume"""
        self._show_volume = True
        return self
    
    def render_chart(self):
        """Renderiza o gráfico completo"""
        # Se nada foi especificado, mostra tudo
        if not self._show_price and not self._show_volume:
            self._show_price = True
            self._show_volume = True
        
        # Calcula número de linhas e suas alturas
        rows = int(self._show_price) + int(self._show_volume)
        row_heights = []
        
        if self._show_price:
            row_heights.append(0.7 if self._show_volume else 1.0)
        if self._show_volume:
            row_heights.append(0.3 if self._show_price else 1.0)
        
        # Cria subplots
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=self._get_subplot_titles()
        )
        
        current_row = 1
        
        # Adiciona gráfico de preços
        if self._show_price:
            self._add_candlestick(fig, current_row)
            current_row += 1
        
        # Adiciona gráfico de volume
        if self._show_volume:
            self._add_volume_bars(fig, current_row)
        
        # Configurações de layout
        self._configure_layout(fig)
        
        # Renderiza no Streamlit
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )
    
    def _get_subplot_titles(self):
        """Retorna títulos dos subplots"""
        titles = []
        if self._show_price:
            titles.append("Preço (OHLC)")
        if self._show_volume:
            titles.append("Volume")
        return titles
    
    def _add_candlestick(self, fig, row: int):
        """Adiciona candlestick chart"""
        # Prepara customdata para hover
        hover_data = pd.DataFrame({
            'open': self.df['Open'],
            'high': self.df['High'],
            'low': self.df['Low'],
            'close': self.df['Close']
        })
        
        fig.add_trace(
            go.Candlestick(
                x=self.df.index,
                open=self.df['Open'],
                high=self.df['High'],
                low=self.df['Low'],
                close=self.df['Close'],
                name='OHLC',
                customdata=hover_data.values,
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d}</b><br>"
                    "Abertura: $%{customdata[0]:.2f}<br>"
                    "Máxima: $%{customdata[1]:.2f}<br>"
                    "Mínima: $%{customdata[2]:.2f}<br>"
                    "Fechamento: $%{customdata[3]:.2f}<br>"
                    "<extra></extra>"
                ),
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=row,
            col=1
        )
        
        fig.update_yaxes(title_text="Preço ($)", row=row, col=1)
    
    def _add_volume_bars(self, fig, row: int):
        """Adiciona barras de volume"""
        if 'Volume' not in self.df.columns:
            # Se não há volume, adiciona anotação
            fig.add_annotation(
                text="Dados de volume não disponíveis",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.15,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            return
        
        # Determina cores baseado em alta/baixa
        colors = [
            '#26a69a' if close >= open_price else '#ef5350'
            for close, open_price in zip(self.df['Close'], self.df['Open'])
        ]
        
        fig.add_trace(
            go.Bar(
                x=self.df.index,
                y=self.df['Volume'],
                name='Volume',
                marker_color=colors,
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d}</b><br>"
                    "Volume: %{y:,.0f}<br>"
                    "<extra></extra>"
                ),
                opacity=0.7
            ),
            row=row,
            col=1
        )
        
        fig.update_yaxes(title_text="Volume", row=row, col=1)
    
    def _configure_layout(self, fig):
        """Configura layout geral do gráfico"""
        fig.update_layout(
            title={
                'text': self.title or "Análise Financeira",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            height=self.height,
            xaxis_rangeslider_visible=self.show_range_slider,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            ),
            margin=dict(l=60, r=40, t=80, b=40),
            template='plotly_white',
            font=dict(family="Arial, sans-serif")
        )
        
        # Configurações dos eixos
        fig.update_xaxes(
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            showline=True,
            showgrid=True,
            gridcolor='lightgray'
        )
        
        fig.update_yaxes(
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            showline=True,
            showgrid=True,
            gridcolor='lightgray'
        )