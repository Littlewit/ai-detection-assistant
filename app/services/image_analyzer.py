"""图像分析服务 - 多模态产品识别与拆分图渲染（玩具检测专用）"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from dashscope import MultiModalConversation
from app.config import get_settings


# 材质配色方案
MATERIAL_COLORS = {
    "塑料": "#4FC3F7",
    "金属": "#90A4AE",
    "纺织": "#FFB74D",
    "纸品": "#A5D6A7",
    "木材": "#BCAAA4",
    "陶瓷": "#CE93D8",
    "电子": "#EF5350",
    "橡胶": "#FFF176",
    "皮革": "#D7CCC8",
    "标签": "#80CBC4",
    "其他": "#E0E0E0",
}

SPLIT_ANALYSIS_PROMPT = """
你是一名资深玩具检测工程师，所在的实验室拥有 CNAS/CMA/CPSC 资质，专业从事玩具及儿童用品检测。

请仔细观察该产品图片，按照玩具检测样板拆分规范，将产品拆分为独立的检测组件/材质组。

【拆分原则】
1. 按材质分组：相同材质的部件归入同一组（如所有塑料件归为一组）
2. 按功能区分：主体部件、配件、包装材料、说明文档分别列出
3. 关注安全风险：小零件（窒息风险）、电池、磁铁、绳索等须单独标注
4. 涂层/表面处理：如有喷漆、电镀、印刷，需单独作为"涂层/表面处理"组件

【检测标准参考（玩具类）】
- EN 71-1: 机械和物理性能
- EN 71-2: 易燃性
- EN 71-3: 特定元素迁移（19类元素）
- EN 62115: 电动玩具安全
- ASTM F963: 美国玩具安全标准
- GB 6675: 中国玩具安全标准（基本规范）
- GB 6675.2: 机械与物理性能
- GB 6675.3: 易燃性能
- GB 6675.4: 特定元素的迁移
- GB 19865: 电动玩具安全
- REACH: 化学品注册（SVHC 高度关注物质）
- RoHS 2.0: 有害物质限制（适用于含电子元件玩具）
- CPSIA: 美国消费品安全改善法（铅含量/邻苯二甲酸酯）
- 加州65: 加州安全饮用水和有毒物质执行法

【输出 JSON 格式】
{
  "product_name": "产品名称（如：积木拼装玩具）",
  "product_category": "产品类别（如：积木/毛绒玩具/电动玩具/塑胶玩具/金属玩具/纸质玩具）",
  "age_group": "适用年龄段（如：3岁以上/6岁以上/14岁以上，根据产品标识或判断）",
  "components": [
    {
      "name": "组件名称（如：塑料积木块）",
      "material": "具体材质（如：ABS塑料）",
      "material_category": "材质大类（塑料/金属/纺织/纸品/木材/陶瓷/电子/橡胶/皮革/标签/其他）",
      "color": "主色（如：红色/蓝色/多色/白色/绿色/透明）",
      "quantity": 1,
      "position": "在整体产品中的位置描述",
      "is_small_part": false,
      "safety_risk": "安全风险说明（如：小零件-窒息风险/电池-化学泄漏/磁铁-吞食风险/无）",
      "test_items": ["EN 71-1 机械物理性能", "EN 71-2 易燃性", "EN 71-3 特定元素迁移"],
      "applicable_standards": ["EN 71", "GB 6675", "ASTM F963"]
    }
  ],
  "safety_warnings": ["窒息风险-含小零件，不适合3岁以下儿童", "其他安全警示"],
  "overall_structure": "整体结构描述"
}

请仅输出 JSON，不要包含其他内容。
"""


def analyze_product_image(image_path: str) -> dict:
    """分析产品图片，生成拆分结构（使用 DashScope MultiModalConversation 原生 API）"""
    settings = get_settings()

    messages = [
        {
            "role": "user",
            "content": [
                {"text": SPLIT_ANALYSIS_PROMPT},
                {"image": f"file://{image_path}"},
            ],
        }
    ]

    response = MultiModalConversation.call(
        model=settings.qwen_vl_model,
        messages=messages,
        api_key=settings.dashscope_api_key,
    )

    if response.status_code != 200:
        raise RuntimeError(f"VL model error: {response.code} - {response.message}")

    content = response.output.choices[0].message["content"][0]["text"].strip()
    # 清理 markdown 代码块
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return json.loads(content)


def render_split_diagram(analysis_result: dict, output_path: str) -> str:
    """根据拆分分析结果渲染专业的样板拆分示意图

    布局设计（从上到下）:
    ┌─────────────────────────────────┐
    │        产品名称 + 类别          │  标题区
    ├─────────────────────────────────┤
    │  ┌──────────┐                   │
    │  │ 产品图标  │──→ 按材质分组     │  拆分树状图
    │  └──────────┘    塑料 │ 金属 │..│
    ├─────────────────────────────────┤
    │    检测项目矩阵                  │  底部汇总表
    └─────────────────────────────────┘
    """
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Zen Hei", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    product_name = analysis_result.get("product_name", "未知产品")
    product_category = analysis_result.get("product_category", "")
    age_group = analysis_result.get("age_group", "")
    components = analysis_result.get("components", [])
    safety_warnings = analysis_result.get("safety_warnings", [])
    n = len(components)

    # 动态计算画布高度
    base_height = 14
    extra_per_component = 1.0
    fig_height = base_height + n * extra_per_component
    fig, ax = plt.subplots(1, 1, figsize=(16, fig_height))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, fig_height)
    ax.axis("off")
    fig.patch.set_facecolor("#FAFAFA")

    # ===== 1. 标题区域 =====
    title_y = fig_height - 1.2
    ax.text(8, title_y, f"样板拆分图", fontsize=20, fontweight="bold",
            ha="center", va="center", color="#1a56db")

    subtitle_parts = [product_name]
    if product_category:
        subtitle_parts.append(product_category)
    if age_group:
        subtitle_parts.append(f"适用{age_group}")
    ax.text(8, title_y - 0.7, "  |  ".join(subtitle_parts),
            fontsize=12, ha="center", va="center", color="#666666")

    # 分割线
    line_y = title_y - 1.2
    ax.plot([1, 15], [line_y, line_y], color="#E0E0E0", linewidth=2)

    # ===== 2. 产品 → 组件拆分区域 =====
    # 产品框（左侧）
    product_box_x, product_box_y = 1.5, line_y - 2.5
    product_box_w, product_box_h = 3.0, 2.0
    product_rect = patches.FancyBboxPatch(
        (product_box_x, product_box_y), product_box_w, product_box_h,
        boxstyle="round,pad=0.15", facecolor="#1a56db", edgecolor="#1a56db",
        linewidth=2, alpha=0.9,
    )
    ax.add_patch(product_rect)
    ax.text(product_box_x + product_box_w / 2, product_box_y + product_box_h / 2 + 0.2,
            "产 品", fontsize=14, fontweight="bold", ha="center", va="center", color="white")
    ax.text(product_box_x + product_box_w / 2, product_box_y + product_box_h / 2 - 0.3,
            product_name[:10], fontsize=9, ha="center", va="center", color="#E8F0FE")

    # 箭头从产品指向组件区域
    arrow_start_x = product_box_x + product_box_w + 0.2
    arrow_y = product_box_y + product_box_h / 2

    # 组件按材质分组
    material_groups = {}
    for comp in components:
        mat_cat = comp.get("material_category", "其他")
        if mat_cat not in material_groups:
            material_groups[mat_cat] = []
        material_groups[mat_cat].append(comp)

    group_names = list(material_groups.keys())
    num_groups = len(group_names)

    # 组件区域起始
    comp_area_x = 6.0
    comp_area_top = line_y - 1.5
    group_spacing = 2.8
    comp_spacing = 1.1

    current_y = comp_area_top

    for mat_name, comps in material_groups.items():
        mat_color = MATERIAL_COLORS.get(mat_name, MATERIAL_COLORS["其他"])

        # 材质分组标签
        group_label_rect = patches.FancyBboxPatch(
            (comp_area_x, current_y - 0.6), 2.0, 0.5,
            boxstyle="round,pad=0.08", facecolor=mat_color, edgecolor="#999999",
            linewidth=1, alpha=0.85,
        )
        ax.add_patch(group_label_rect)
        ax.text(comp_area_x + 1.0, current_y - 0.35, f"{mat_name}组",
                fontsize=10, fontweight="bold", ha="center", va="center", color="#333333")

        # 从产品框画箭头到材质组
        ax.annotate("", xy=(comp_area_x, current_y - 0.35),
                     xytext=(arrow_start_x, arrow_y),
                     arrowprops=dict(arrowstyle="->", color="#BDBDBD",
                                     lw=1.5, connectionstyle="arc3,rad=0.1"))

        current_y -= 0.9

        # 各组件
        for ci, comp in enumerate(comps):
            name = comp.get("name", f"组件{ci+1}")
            material = comp.get("material", "")
            qty = comp.get("quantity", 1)
            color_name = comp.get("color", "")
            is_small = comp.get("is_small_part", False)

            # 组件框
            comp_label = f"{name}"
            if material:
                comp_label += f" ({material})"
            if qty > 1:
                comp_label += f" ×{qty}"

            comp_rect = patches.FancyBboxPatch(
                (comp_area_x + 2.3, current_y - 0.4), 4.5, 0.65,
                boxstyle="round,pad=0.06", facecolor="white",
                edgecolor=mat_color, linewidth=1.5,
            )
            ax.add_patch(comp_rect)

            # 组件名称
            ax.text(comp_area_x + 2.5, current_y - 0.08, comp_label,
                    fontsize=9, fontweight="bold", ha="left", va="center", color="#333333")

            # 小零件标记
            if is_small:
                ax.text(comp_area_x + 6.5, current_y - 0.08, "⚠️小零件",
                        fontsize=7, ha="left", va="center", color="#dc2626")

            # 检测项目标注（右侧）
            test_items = comp.get("test_items", [])
            if test_items:
                items_text = " / ".join(test_items[:3])
                if len(test_items) > 3:
                    items_text += f" +{len(test_items)-3}"
                ax.text(comp_area_x + 7.2, current_y - 0.08, items_text,
                        fontsize=7, ha="left", va="center", color="#666666",
                        style="italic")

            # 连接线（材质组 → 组件）
            ax.plot([comp_area_x + 2.0, comp_area_x + 2.3],
                    [current_y - 0.08, current_y - 0.08],
                    color=mat_color, linewidth=1.5)

            current_y -= comp_spacing

        current_y -= 0.3  # 组间距

    # ===== 3. 安全风险警示区 =====
    if safety_warnings:
        warn_y = current_y - 0.5
        ax.plot([1, 15], [warn_y + 0.3, warn_y + 0.3], color="#E0E0E0", linewidth=1)
        ax.text(8, warn_y, "⚠️ 安全警示", fontsize=11, fontweight="bold",
                ha="center", va="center", color="#dc2626")
        for wi, warning in enumerate(safety_warnings[:4]):
            ax.text(8, warn_y - 0.5 - wi * 0.45, f"• {warning}",
                    fontsize=9, ha="center", va="center", color="#666666")
        current_y = warn_y - 0.5 - len(safety_warnings[:4]) * 0.45 - 0.5

    # ===== 4. 底部检测项目汇总矩阵 =====
    matrix_y = current_y - 0.5
    ax.plot([1, 15], [matrix_y + 0.3, matrix_y + 0.3], color="#E0E0E0", linewidth=1)
    ax.text(8, matrix_y, "检测项目汇总", fontsize=12, fontweight="bold",
            ha="center", va="center", color="#1a56db")

    # 收集所有检测标准和项目
    all_standards = set()
    all_tests = set()
    for comp in components:
        for s in comp.get("applicable_standards", []):
            all_standards.add(s)
        for t in comp.get("test_items", []):
            all_tests.add(t)

    standards_list = sorted(all_standards)
    if standards_list:
        ax.text(8, matrix_y - 0.6,
                "适用标准：" + " | ".join(standards_list[:8]),
                fontsize=9, ha="center", va="center", color="#4b5563")

    tests_list = sorted(all_tests)
    if tests_list:
        tests_text = "检测项目：" + " | ".join(tests_list[:10])
        if len(tests_list) > 10:
            tests_text += f" 等{len(tests_list)}项"
        ax.text(8, matrix_y - 1.1, tests_text,
                fontsize=8, ha="center", va="center", color="#666666")

    # ===== 5. 底部署名 =====
    settings = get_settings()
    ax.text(8, 0.5,
            f"CNAS {settings.lab_cnas_id} | CMA {settings.lab_cma_id} | "
            f"共 {n} 个组件 / {num_groups} 种材质",
            fontsize=8, ha="center", va="center", color="#AAAAAA")

    plt.tight_layout(pad=1.0)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return output_path
