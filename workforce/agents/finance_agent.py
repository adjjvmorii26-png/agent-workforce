from __future__ import annotations

from .base import AgentContext, AgentResult, BaseAgent
from ..bus import Event


class FinanceAgent(BaseAgent):
    """Power agent for financial governance and capital allocation.
    
    This agent manages the organism's financial ecosystem - handling cash flow,
    portfolio optimization, risk assessment across crypto/NFT/stock avenues, and
    ensuring financial sustainability. It operates as the "circulatory system" of
    financial decision-making, coordinating between investment, expenditure, and
    growth strategies.
    """
    
    name = "finance"
    role = "financial governance and capital allocation"
    capabilities = [
        "portfolio-optimization",
        "risk-assessment",
        "cashflow-management",
        "investment-strategy",
        "asset-allocation",
        "financial-compliance",
        "revenue-forecasting",
    ]
    tool_names = []

    def __init__(self, llm, registry, memory, bus, run_id: str) -> None:
        super().__init__(llm, registry, memory, bus, run_id)
        self._portfolio_history = []
        self._risk_threshold = 0.7
        self._allocation_strategies = {
            "conservative": {"crypto": 0.4, "stablecoin": 0.4, "cash": 0.2},
            "balanced": {"crypto": 0.6, "stablecoin": 0.2, "growth": 0.2},
            "aggressive": {"crypto": 0.8, "growth": 0.15, "stablecoin": 0.05},
        }

    def system_prompt(self) -> str:
        return (
            "You are the FINANCE AGENT of IXPANSION — the organism's capital "
            "governor. You manage the circulatory flow of money, crypto, and assets "
            "through the system. You optimize portfolio allocation across crypto, NFTs, "
            "stocks and cash, assess risks in real-time, and ensure financial sustainability. "
            "You are not a trader; you are a steward of the organism's economic health. "
            "Every decision must support the greater organism, not individual gain. "
            "Report portfolio state, rebalancing needs, and risk warnings with precision."
        )

    def _assess_portfolio_health(self, portfolio: dict) -> dict:
        """Assess the health of the organism's portfolio."""
        assets = portfolio.get("assets", {})
        nfts = portfolio.get("nfts", {})
        
        crypto_holdings = sum(
            float(v) for k, v in assets.items() 
            if k in ("BTC", "ETH", "SOL")
        )
        nft_value = sum(
            float(v.get("value", 0)) for k, v in nfts.items()
        )
        total_value = crypto_holdings + nft_value
        
        if total_value == 0:
            return {"health": 0, "risk": "unknown", "diversification": "none"}
        
        crypto_ratio = crypto_holdings / total_value if total_value > 0 else 0
        nft_ratio = nft_value / total_value if total_value > 0 else 0
        
        # Assess diversification
        asset_types = len([k for k in assets.keys() if k not in ("NFT-001",)]) + len(nfts)
        diversification = "good" if asset_types >= 3 else "limited" if asset_types >= 1 else "none"
        
        # Risk assessment based on volatility indicators
        risk = "low" if crypto_ratio < 0.5 and nft_ratio < 0.3 else "medium" if crypto_ratio < 0.7 else "high"
        
        health_score = min(100, int((1 - abs(crypto_ratio - 0.5)) * 100))
        
        return {
            "health": health_score,
            "risk": risk,
            "diversification": diversification,
            "crypto_ratio": round(crypto_ratio, 3),
            "nft_ratio": round(nft_ratio, 3),
            "total_value_estimate": round(total_value, 2),
        }

    def _generate_allocation_recommendation(self, portfolio: dict) -> dict:
        """Generate allocation recommendations based on current state."""
        health = self._assess_portfolio_health(portfolio)
        current_strategy = "balanced"  # default
        
        if health["risk"] == "high" and health["crypto_ratio"] > 0.7:
            current_strategy = "conservative"
        elif health["risk"] == "medium" and health["crypto_ratio"] > 0.5:
            current_strategy = "balanced"
        
        strategy = self._allocation_strategies.get(current_strategy, self._allocation_strategies["balanced"])
        
        assets = portfolio.get("assets", {})
        nfts = portfolio.get("nfts", {})
        
        recommendations = []
        for asset, pct in strategy.items():
            if asset == "crypto":
                current_amount = sum(float(v) for k, v in assets.items() if k in ("BTC", "ETH", "SOL"))
                target = max(0, round(pct * health["total_value_estimate"] / 50000, 4))  # normalized
                if current_amount > 0:
                    recommendations.append(f"CRYPTO: maintain ~{target} BTC-equivalent")
            elif asset == "stablecoin":
                recommendations.append(f"STABLECOIN: allocate ~{health['total_value_estimate'] * pct:.2f} USDT for liquidity")
            elif asset == "growth":
                # Look for opportunities in NFTs or new assets
                nft_count = len(nfts)
                if nft_count > 0:
                    recommendations.append(f"GROWTH: explore NFT flipping opportunities (currently {nft_count} NFTs)")
                else:
                    recommendations.append("GROWTH: scout for undervalued NFT projects or stocks")
        
        # Add cash flow recommendations
        revenue_total = sum(
            float(t.get("amount", 0)) for t in portfolio.get("revenue_streams", [])
            if t.get("type") == "revenue"
        )
        expense_total = sum(
            float(t.get("amount", 0)) for t in portfolio.get("expenditure_streams", [])
            if t.get("type") == "expenditure"
        )
        
        net_cashflow = revenue_total - expense_total
        if net_cashflow < 0:
            recommendations.append(f"CASHFLOW: negative net ${net_cashflow:.2f}/cycle - identify expenditure reductions")
        elif net_cashflow > 0:
            recommendations.append(f"CASHFLOW: positive net ${net_cashflow:.2f}/cycle - consider reinvestment or reserve building")
        
        return {
            "current_strategy": current_strategy,
            "recommendations": recommendations,
            "health": health,
        }

    def run(self, context: AgentContext) -> AgentResult:
        # Try to load current portfolio and financial data
        try:
            import json
            from pathlib import Path
            
            cashflow_dir = Path("ixpansion/content_output/cashflow")
            portfolio = {}
            if (cashflow_dir / "portfolio.json").is_file():
                portfolio = json.loads((cashflow_dir / "portfolio.json").read_text())
            
            # Generate analysis and recommendations
            analysis = self._assess_portfolio_health(portfolio)
            recommendations = self._generate_allocation_recommendation(portfolio)
            
            # Publish financial signal to the bus
            summary = (
                f"finance: portfolio health={analysis['health']}, "
                f"risk={analysis['risk']}, strategy={recommendations['current_strategy']}, "
                f"diversification={analysis['diversification']}\n"
            )
            summary += "Recommendations:\n"
            for rec in recommendations["recommendations"][:5]:  # top 5
                summary += f"  - {rec}\n"
            
            self.bus.publish(Event(
                type="finance_signal",
                payload={
                    "topic": "portfolio-analysis",
                    "body": summary,
                    "agent": "finance",
                    "health": analysis,
                    "strategy": recommendations["current_strategy"],
                },
                source="finance",
            ))
            
            return AgentResult(
                output=summary.strip(),
                message_count=1,
            )
            
        except Exception as e:
            error_msg = f"finance agent error: {str(e)}"
            self.bus.publish(Event(
                type="finance_signal",
                payload={"topic": "error", "body": error_msg, "agent": "finance"},
                source="finance",
            ))
            return AgentResult(output=error_msg, message_count=1)
