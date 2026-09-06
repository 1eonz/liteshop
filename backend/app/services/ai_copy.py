"""AI 商品文案扩展点，默认使用本地确定性模板。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductCopySuggestion:
    """文案建议结果。"""

    title: str
    subtitle: str
    description: str
    provider: str


class ProductCopyProvider:
    """可替换的商品文案生成器接口。"""

    async def generate(self, *, name: str, category: str = "") -> ProductCopySuggestion:
        """使用本地模板生成安全草稿，不调用外部网络。"""
        context = category.strip() or "日常好物"
        return ProductCopySuggestion(
            title=name.strip() or context,
            subtitle=f"{context}，为每一天提供恰到好处的体验",
            description=f"这是一款面向真实生活场景打造的{context}，材质可靠、使用简单，适合稳定融入日常。",
            provider="local-template",
        )


product_copy_provider = ProductCopyProvider()
