"""内存数据集存储：演示样本可被真实导入资料整体替换。

真实落地时通过 POST /api/dataset/import 上传符合 examples/dataset.example.json
格式的货源资料；导入后 is_demo=False，审计与界面会移除"演示样本"提示。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .demo_data import build_dataset
from .models import EvidenceDocument, SourceProduct


@dataclass
class DatasetStore:
    products: list[SourceProduct] = field(default_factory=list)
    documents: list[EvidenceDocument] = field(default_factory=list)
    is_demo: bool = True

    def reset_demo(self) -> None:
        self.products, self.documents = build_dataset()
        self.is_demo = True

    def replace(self, products: list[SourceProduct], documents: list[EvidenceDocument]) -> None:
        if not products:
            raise ValueError("products 不能为空")
        self.products = products
        self.documents = documents
        self.is_demo = False

    def product_index(self) -> dict[str, SourceProduct]:
        return {p.id: p for p in self.products}


store = DatasetStore()
store.reset_demo()
