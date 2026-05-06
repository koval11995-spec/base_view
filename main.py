import streamlit as st
import json
from typing import Dict, List, Optional


class TreatmentPlanner:
    def __init__(self, knowledge_base_path: Optional[str] = None):
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        else:
            self.knowledge_base = {"disease": []}

    def load_knowledge_base(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

    def get_diseases(self) -> List[str]:
        return [d["name"] for d in self.knowledge_base["disease"]]

    def get_types(self, disease_name: str) -> List[Dict]:
        for d in self.knowledge_base["disease"]:
            if d["name"] == disease_name:
                return d.get("type", [])
        return []

    def get_variants(self, disease_name: str, type_name: str) -> List[Dict]:
        types = self.get_types(disease_name)
        for t in types:
            if t["name"] == type_name:
                return t.get("variant", [])
        return []

    def get_stages(self, disease_name: str, type_name: str, variant_name: str) -> List[Dict]:
        variants = self.get_variants(disease_name, type_name)
        variant = next((v for v in variants if v["name"] == variant_name), None)
        if not variant:
            return []
        return variant.get("stage", [])

    def get_methods_from_alternative(self, stage: Dict) -> List[Dict]:
        """Извлекает все методы из списка alternative_groups, добавляя тип метода"""
        methods = []
        for group in stage.get("alternative_groups", []):
            for method_type, key in [("хирургический", "surgical methods"),
                                     ("реабилитационный", "rehabilitation methods"),
                                     ("лекарственный", "medicines")]:
                items = group.get(key, [])
                for item in items:
                    item_copy = item.copy()
                    item_copy["method_type"] = method_type
                    methods.append(item_copy)
        return methods

    def get_methods_from_joint(self, stage: Dict) -> List[Dict]:
        """Извлекает все методы из списка joint_groups, добавляя тип метода и общую информацию группы"""
        methods = []
        for group in stage.get("joint_groups", []):
            joint_indications = group.get("indications", [])
            joint_recommendations = group.get("recommendations", "")
            for method_type, key in [("хирургический", "surgical methods"),
                                     ("реабилитационный", "rehabilitation methods"),
                                     ("лекарственный", "medicines")]:
                items = group.get(key, [])
                for item in items:
                    item_copy = item.copy()
                    item_copy["method_type"] = method_type
                    item_copy["joint_indications"] = joint_indications
                    item_copy["joint_recommendations"] = joint_recommendations
                    methods.append(item_copy)
        return methods

    def search_methods_by_keyword(self, keyword: str) -> List[Dict]:
        results = []
        keyword_lower = keyword.lower()

        for disease in self.knowledge_base["disease"]:
            disease_name = disease["name"]
            for type_obj in disease.get("type", []):
                type_name = type_obj["name"]
                for variant in type_obj.get("variant", []):
                    variant_name = variant["name"]
                    for stage in variant.get("stage", []):
                        stage_name = stage.get("name_stage", "")
                        # Альтернативные методы
                        for method in self.get_methods_from_alternative(stage):
                            if self._method_matches(method, keyword_lower):
                                results.append(self._format_result(
                                    method, disease_name, type_name, variant_name,
                                    stage_name, "alternative"
                                ))
                        # Совместные методы
                        for method in self.get_methods_from_joint(stage):
                            if self._method_matches(method, keyword_lower):
                                results.append(self._format_result(
                                    method, disease_name, type_name, variant_name,
                                    stage_name, "joint"
                                ))
        return results

    def _method_matches(self, method: Dict, keyword_lower: str) -> bool:
        fields_to_check = [
            method.get("name method", ""),
            method.get("active substance", ""),
            method.get("recommendations", ""),
            method.get("dosage", ""),
            method.get("rehabilitation course", ""),
            method.get("joint_recommendations", ""),
            *method.get("indications", []),
            *method.get("used material", []),
        ]
        surgical_access = method.get("surgical access", [])
        if isinstance(surgical_access, list):
            for access in surgical_access:
                if isinstance(access, dict):
                    fields_to_check.append(str(access.get("name", "")))
                    fields_to_check.extend(access.get("indications", []))
                else:
                    fields_to_check.append(str(access))
        elif isinstance(surgical_access, str):
            fields_to_check.append(surgical_access)
        return any(keyword_lower in str(field).lower() for field in fields_to_check)

    def _format_result(self, method: Dict, disease: str, type_name: str, variant: str,
                       stage: str, method_category: str) -> Dict:
        result = {
            "method_name": method.get("name method", method.get("active substance", "Без названия")),
            "disease": disease,
            "type": type_name,
            "variant": variant,
            "stage": stage,
            "method_category": method_category,
            "method_type_detail": method.get("method_type", ""),
            "indications": method.get("indications", []),
            "recommendations": method.get("recommendations", ""),
            "dosage": method.get("dosage", ""),
            "used_material": method.get("used material", []),
            "pages": method.get("pages", []),
            "persuasiveness": method.get("persuasiveness", ""),
            "evidence": method.get("evidence", ""),
            "joint_indications": method.get("joint_indications", []),
            "joint_recommendations": method.get("joint_recommendations", "")
        }
        if "active substance" in method:
            result["active_substance"] = method["active substance"]
        if "surgical access" in method:
            result["surgical_access"] = method["surgical access"]
        if "rehabilitation course" in method:
            result["rehabilitation_course"] = method["rehabilitation course"]
        return result


def display_surgical_access(surgical_access):
    if isinstance(surgical_access, list):
        for access in surgical_access:
            if isinstance(access, dict):
                name = str(access.get('name', ''))
                st.markdown(f"- **{name}**")
                if access.get("indications"):
                    st.write("  Показания: " + ", ".join(access["indications"]))
            else:
                st.markdown(f"- {access}")
    elif isinstance(surgical_access, str):
        st.markdown(f"- {surgical_access}")


def display_method_details(method: Dict, is_joint: bool = False):
    if method.get("active substance"):
        st.write(f"**Действующее вещество:** {method['active substance']}")

    if method.get("indications"):
        st.write("**Показания:**")
        for ind in method["indications"]:
            st.write(f"- {ind}")

    if is_joint and method.get("joint_indications"):
        st.write("**Общие показания блока:**")
        for ind in method["joint_indications"]:
            st.write(f"- {ind}")

    if method.get("recommendations"):
        st.write(f"**Рекомендации:** {method['recommendations']}")
    if is_joint and method.get("joint_recommendations"):
        st.write(f"**Общие рекомендации блока:** {method['joint_recommendations']}")

    if method.get("dosage"):
        st.write(f"**Дозировка:** {method['dosage']}")

    if method.get("surgical access"):
        st.write("**Хирургические доступы:**")
        display_surgical_access(method["surgical access"])

    if method.get("used material"):
        st.write("**Используемые материалы:**")
        for mat in method["used material"]:
            st.write(f"- {mat}")

    if method.get("rehabilitation course"):
        st.write(f"**Курс реабилитации:** {method['rehabilitation course']}")

    meta = []
    if method.get("persuasiveness"):
        meta.append(f"Убедительность: {method['persuasiveness']}")
    if method.get("evidence"):
        meta.append(f"Доказательность: {method['evidence']}")
    if method.get("pages"):
        meta.append(f"Страницы: {', '.join(map(str, method['pages']))}")
    if meta:
        st.write("**Доказательная база:** " + " | ".join(meta))


def generate_treatment_report(stage: Dict, selected_type: Dict, variant_name: str) -> str:
    def format_surgical_access(surgical_access):
        lines = []
        if isinstance(surgical_access, list):
            for access in surgical_access:
                if isinstance(access, dict):
                    name = str(access.get('name', ''))
                    lines.append(f"- **{name}**")
                    if access.get("indications"):
                        lines.append("  Показания: " + ", ".join(access["indications"]))
                else:
                    lines.append(f"- {access}")
        elif isinstance(surgical_access, str):
            lines.append(f"- {surgical_access}")
        return "\n".join(lines)

    report_lines = []
    report_lines.append("# ОТЧЁТ О ПЛАНЕ ЛЕЧЕНИЯ\n")
    report_lines.append("## Основная информация")
    report_lines.append(f"**Тип перелома:** {selected_type['name']}")
    report_lines.append(f"**Вариант:** {variant_name}")
    report_lines.append(f"**Код МКБ-10:** {', '.join(selected_type.get('ICD-10_code', []))}")
    report_lines.append(f"**Этап:** {stage['name_stage']}\n")

    alt_methods = TreatmentPlanner().get_methods_from_alternative(stage)  # используем статический контекст, не важно
    if alt_methods:
        report_lines.append("## Альтернативные методы")
        for method in alt_methods:
            name = method.get("name method", method.get("active substance", "Без названия"))
            report_lines.append(f"\n### {name} ({method.get('method_type', '')})")
            if method.get("indications"):
                report_lines.append("**Показания:**")
                for ind in method["indications"]:
                    report_lines.append(f"- {ind}")
            if method.get("active substance"):
                report_lines.append(f"**Действующее вещество:** {method['active substance']}")
            if method.get("dosage"):
                report_lines.append(f"**Дозировка:** {method['dosage']}")
            if method.get("recommendations"):
                report_lines.append(f"**Рекомендации:** {method['recommendations']}")
            if method.get("surgical access"):
                report_lines.append("**Хирургические доступы:**")
                report_lines.append(format_surgical_access(method["surgical access"]))
            if method.get("used material"):
                report_lines.append("**Используемые материалы:**")
                for mat in method["used material"]:
                    report_lines.append(f"- {mat}")
            if method.get("rehabilitation course"):
                report_lines.append(f"**Курс реабилитации:** {method['rehabilitation course']}")
            pages = method.get("pages", [])
            if pages:
                report_lines.append(f"**Страницы:** {', '.join(map(str, pages))}")
            if method.get("persuasiveness"):
                report_lines.append(f"**Убедительность:** {method['persuasiveness']}")
            if method.get("evidence"):
                report_lines.append(f"**Доказательность:** {method['evidence']}")

    joint_methods = TreatmentPlanner().get_methods_from_joint(stage)
    if joint_methods:
        report_lines.append("\n## Совместные методы")
        # Выводим общую информацию первой группы (если нужно)
        first_group = stage.get("joint_groups", [{}])[0]
        if first_group.get("indications"):
            report_lines.append("**Общие показания блока:**")
            for ind in first_group["indications"]:
                report_lines.append(f"- {ind}")
        if first_group.get("recommendations"):
            report_lines.append(f"**Общие рекомендации блока:** {first_group['recommendations']}")

        for method in joint_methods:
            name = method.get("name method", method.get("active substance", "Без названия"))
            report_lines.append(f"\n### {name} ({method.get('method_type', '')})")
            if method.get("indications"):
                report_lines.append("**Показания:**")
                for ind in method["indications"]:
                    report_lines.append(f"- {ind}")
            if method.get("active substance"):
                report_lines.append(f"**Действующее вещество:** {method['active substance']}")
            if method.get("dosage"):
                report_lines.append(f"**Дозировка:** {method['dosage']}")
            if method.get("recommendations"):
                report_lines.append(f"**Рекомендации:** {method['recommendations']}")
            if method.get("surgical access"):
                report_lines.append("**Хирургические доступы:**")
                report_lines.append(format_surgical_access(method["surgical access"]))
            if method.get("used material"):
                report_lines.append("**Используемые материалы:**")
                for mat in method["used material"]:
                    report_lines.append(f"- {mat}")
            if method.get("rehabilitation course"):
                report_lines.append(f"**Курс реабилитации:** {method['rehabilitation course']}")
            pages = method.get("pages", [])
            if pages:
                report_lines.append(f"**Страницы:** {', '.join(map(str, pages))}")
            if method.get("persuasiveness"):
                report_lines.append(f"**Убедительность:** {method['persuasiveness']}")
            if method.get("evidence"):
                report_lines.append(f"**Доказательность:** {method['evidence']}")

    return "\n".join(report_lines)


def generate_treatment_report_html(stage: Dict, selected_type: Dict, variant_name: str) -> str:
    # аналогично generate_treatment_report, но с HTML
    def format_surgical_access_html(surgical_access):
        if isinstance(surgical_access, list):
            items = []
            for access in surgical_access:
                if isinstance(access, dict):
                    name = str(access.get('name', ''))
                    item = f"<li><b>{name}</b>"
                    if access.get("indications"):
                        item += "<ul><li>Показания: " + ", ".join(access["indications"]) + "</li></ul>"
                    item += "</li>"
                    items.append(item)
                else:
                    items.append(f"<li>{access}</li>")
            return "<ul>" + "".join(items) + "</ul>"
        elif isinstance(surgical_access, str):
            return f"<ul><li>{surgical_access}</li></ul>"
        return ""

    html_parts = []
    html_parts.append("<html><head><meta charset='utf-8'><title>План лечения</title>")
    html_parts.append("<style>body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }")
    html_parts.append("h1 { color: #2c3e50; } h2 { color: #2980b9; border-bottom: 1px solid #ddd; padding-bottom: 5px; }")
    html_parts.append("h3 { color: #27ae60; } ul { margin: 5px 0; } li { margin: 2px 0; }")
    html_parts.append(".meta { font-size: 0.9em; color: #7f8c8d; }</style></head><body>")

    html_parts.append("<h1>ОТЧЁТ О ПЛАНЕ ЛЕЧЕНИЯ</h1>")
    html_parts.append("<h2>Основная информация</h2>")
    html_parts.append(f"<p><b>Тип перелома:</b> {selected_type['name']}<br>")
    html_parts.append(f"<b>Вариант:</b> {variant_name}<br>")
    html_parts.append(f"<b>Код МКБ-10:</b> {', '.join(selected_type.get('ICD-10_code', []))}<br>")
    html_parts.append(f"<b>Этап:</b> {stage['name_stage']}</p>")

    planner = TreatmentPlanner()
    alt_methods = planner.get_methods_from_alternative(stage)
    if alt_methods:
        html_parts.append("<h2>Альтернативные методы</h2>")
        for method in alt_methods:
            name = method.get("name method", method.get("active substance", "Без названия"))
            html_parts.append(f"<h3>{name} ({method.get('method_type', '')})</h3>")
            if method.get("indications"):
                html_parts.append("<p><b>Показания:</b></p><ul>")
                for ind in method["indications"]:
                    html_parts.append(f"<li>{ind}</li>")
                html_parts.append("</ul>")
            if method.get("active substance"):
                html_parts.append(f"<p><b>Действующее вещество:</b> {method['active substance']}</p>")
            if method.get("dosage"):
                html_parts.append(f"<p><b>Дозировка:</b> {method['dosage']}</p>")
            if method.get("recommendations"):
                html_parts.append(f"<p><b>Рекомендации:</b> {method['recommendations']}</p>")
            if method.get("surgical access"):
                html_parts.append("<p><b>Хирургические доступы:</b></p>")
                html_parts.append(format_surgical_access_html(method["surgical access"]))
            if method.get("used material"):
                html_parts.append("<p><b>Используемые материалы:</b></p><ul>")
                for mat in method["used material"]:
                    html_parts.append(f"<li>{mat}</li>")
                html_parts.append("</ul>")
            if method.get("rehabilitation course"):
                html_parts.append(f"<p><b>Курс реабилитации:</b> {method['rehabilitation course']}</p>")
            meta = []
            if method.get("persuasiveness"):
                meta.append(f"Убедительность: {method['persuasiveness']}")
            if method.get("evidence"):
                meta.append(f"Доказательность: {method['evidence']}")
            if method.get("pages"):
                meta.append(f"Страницы: {', '.join(map(str, method['pages']))}")
            if meta:
                html_parts.append(f"<p class='meta'>{' | '.join(meta)}</p>")

    joint_methods = planner.get_methods_from_joint(stage)
    if joint_methods:
        html_parts.append("<h2>Совместные методы</h2>")
        first_group = stage.get("joint_groups", [{}])[0]
        if first_group.get("indications"):
            html_parts.append("<p><b>Общие показания блока:</b></p><ul>")
            for ind in first_group["indications"]:
                html_parts.append(f"<li>{ind}</li>")
            html_parts.append("</ul>")
        if first_group.get("recommendations"):
            html_parts.append(f"<p><b>Общие рекомендации блока:</b> {first_group['recommendations']}</p>")
        for method in joint_methods:
            name = method.get("name method", method.get("active substance", "Без названия"))
            html_parts.append(f"<h3>{name} ({method.get('method_type', '')})</h3>")
            if method.get("indications"):
                html_parts.append("<p><b>Показания:</b></p><ul>")
                for ind in method["indications"]:
                    html_parts.append(f"<li>{ind}</li>")
                html_parts.append("</ul>")
            if method.get("active substance"):
                html_parts.append(f"<p><b>Действующее вещество:</b> {method['active substance']}</p>")
            if method.get("dosage"):
                html_parts.append(f"<p><b>Дозировка:</b> {method['dosage']}</p>")
            if method.get("recommendations"):
                html_parts.append(f"<p><b>Рекомендации:</b> {method['recommendations']}</p>")
            if method.get("surgical access"):
                html_parts.append("<p><b>Хирургические доступы:</b></p>")
                html_parts.append(format_surgical_access_html(method["surgical access"]))
            if method.get("used material"):
                html_parts.append("<p><b>Используемые материалы:</b></p><ul>")
                for mat in method["used material"]:
                    html_parts.append(f"<li>{mat}</li>")
                html_parts.append("</ul>")
            if method.get("rehabilitation course"):
                html_parts.append(f"<p><b>Курс реабилитации:</b> {method['rehabilitation course']}</p>")
            meta = []
            if method.get("persuasiveness"):
                meta.append(f"Убедительность: {method['persuasiveness']}")
            if method.get("evidence"):
                meta.append(f"Доказательность: {method['evidence']}")
            if method.get("pages"):
                meta.append(f"Страницы: {', '.join(map(str, method['pages']))}")
            if meta:
                html_parts.append(f"<p class='meta'>{' | '.join(meta)}</p>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def main():
    st.set_page_config(page_title="Клиническая рекомендация", page_icon="🏥", layout="wide")

    if 'planner' not in st.session_state:
        json_path = "голень н2.json"   # <-- новый файл
        st.session_state.planner = TreatmentPlanner(json_path)

    planner = st.session_state.planner

    st.title("🏥 Автоматически извлечённая информация из клинической рекомендации")
    st.markdown("---")

    with st.sidebar:
        st.header("Навигация")
        app_mode = st.radio(
            "Выберите режим работы:",
            ["Планирование лечения", "Поиск методов", "База знаний"]
        )
        st.markdown("---")

    if app_mode == "Планирование лечения":
        st.header("Планирование лечения")

        diseases = planner.get_diseases()
        if not diseases:
            st.error("База знаний не загружена или пуста. Проверьте путь к файлу.")
            return

        col1, col2, col3 = st.columns([0.3, 0.3, 0.3])
        with col1:
            selected_disease = st.selectbox("Заболевание:", diseases)

        if selected_disease:
            types = planner.get_types(selected_disease)
            type_names = [t["name"] for t in types]
            with col2:
                selected_type_name = st.selectbox("Тип перелома:", type_names)

            if selected_type_name:
                selected_type = next(t for t in types if t["name"] == selected_type_name)
                st.info(f"**Код МКБ-10:** {', '.join(selected_type.get('ICD-10_code', []))}")

                variants = planner.get_variants(selected_disease, selected_type_name)
                variant_names = [v["name"] for v in variants]
                with col3:
                    selected_variant_name = st.selectbox("Вариант (классификация):", variant_names)

                if selected_variant_name:
                    stages = planner.get_stages(selected_disease, selected_type_name, selected_variant_name)

                    if stages:
                        st.markdown("---")
                        st.header("📋 План лечения")

                        stage_names = [s["name_stage"] for s in stages]
                        tabs = st.tabs(stage_names)

                        for i, tab in enumerate(tabs):
                            with tab:
                                stage = stages[i]
                                st.subheader(stage["name_stage"])

                                # Альтернативные методы
                                alt_methods = planner.get_methods_from_alternative(stage)
                                if alt_methods:
                                    st.markdown("### Альтернативные методы")
                                    for method in alt_methods:
                                        with st.expander(f"**{method.get('name method', method.get('active substance', 'Без названия'))}** ({method['method_type']})"):
                                            display_method_details(method)
                                else:
                                    st.info("Альтернативные методы не указаны")

                                # Совместные методы
                                joint_methods = planner.get_methods_from_joint(stage)
                                if joint_methods:
                                    st.markdown("### Совместные методы")
                                    # Общая информация первой группы
                                    first_group = stage.get("joint_groups", [{}])[0]
                                    if first_group.get("indications") or first_group.get("recommendations"):
                                        with st.expander("📌 Общая информация блока"):
                                            if first_group.get("indications"):
                                                st.write("**Показания для всего блока:**")
                                                for ind in first_group["indications"]:
                                                    st.write(f"- {ind}")
                                            if first_group.get("recommendations"):
                                                st.write(f"**Общие рекомендации:** {first_group['recommendations']}")

                                    for method in joint_methods:
                                        with st.expander(f"**{method.get('name method', method.get('active substance', 'Без названия'))}** ({method['method_type']})"):
                                            display_method_details(method, is_joint=True)
                                else:
                                    st.info("Совместные методы не указаны")

                                if st.button(f"📄 Сгенерировать отчёт для этапа «{stage['name_stage']}»"):
                                    report_md = generate_treatment_report(stage, selected_type, selected_variant_name)
                                    report_html = generate_treatment_report_html(stage, selected_type, selected_variant_name)

                                    st.markdown("---")
                                    st.header("📄 Сгенерированный отчёт (Markdown)")
                                    st.markdown(report_md)

                                    col_dl1, col_dl2 = st.columns(2)
                                    with col_dl1:
                                        st.download_button(
                                            label="📥 Скачать Markdown",
                                            data=report_md,
                                            file_name=f"treatment_plan_{selected_variant_name.replace(' ', '_')}_{stage['name_stage'].replace(' ', '_')}.md",
                                            mime="text/markdown"
                                        )
                                    with col_dl2:
                                        st.download_button(
                                            label="📥 Скачать HTML",
                                            data=report_html,
                                            file_name=f"treatment_plan_{selected_variant_name.replace(' ', '_')}_{stage['name_stage'].replace(' ', '_')}.html",
                                            mime="text/html"
                                        )

                    else:
                        st.warning("Для данного варианта нет этапов")

    elif app_mode == "Поиск методов":
        st.header("🔍 Поиск методов лечения")

        search_term = st.text_input(
            "Введите ключевое слово для поиска:",
            placeholder="Например: остеосинтез, цефазолин, реабилитация..."
        )

        if search_term:
            results = planner.search_methods_by_keyword(search_term)

            if results:
                st.write(f"Найдено результатов: {len(results)}")

                for res in results:
                    with st.expander(f"{res['method_name']} ({res['disease']} – {res['stage']})"):
                        st.write(f"**Заболевание:** {res['disease']}")
                        st.write(f"**Тип перелома:** {res['type']}")
                        st.write(f"**Вариант:** {res['variant']}")
                        st.write(f"**Этап:** {res['stage']}")
                        st.write(f"**Категория:** {'Альтернативный' if res['method_category'] == 'alternative' else 'Совместный'} / {res['method_type_detail']}")

                        if res.get("indications"):
                            st.write("**Показания:**")
                            for ind in res["indications"]:
                                st.write(f"- {ind}")

                        if res.get("active_substance"):
                            st.write(f"**Действующее вещество:** {res['active_substance']}")
                        if res.get("dosage"):
                            st.write(f"**Дозировка:** {res['dosage']}")

                        if res.get("recommendations"):
                            st.write(f"**Рекомендации:** {res['recommendations']}")

                        if res.get("surgical_access"):
                            st.write("**Хирургические доступы:**")
                            display_surgical_access(res["surgical_access"])

                        if res.get("used_material"):
                            st.write("**Используемые материалы:**")
                            for mat in res["used_material"]:
                                st.write(f"- {mat}")

                        if res.get("rehabilitation_course"):
                            st.write(f"**Курс реабилитации:** {res['rehabilitation_course']}")

                        if res.get("joint_indications"):
                            st.write("**Общие показания блока:**")
                            for ind in res["joint_indications"]:
                                st.write(f"- {ind}")
                        if res.get("joint_recommendations"):
                            st.write(f"**Общие рекомендации блока:** {res['joint_recommendations']}")

                        if res.get("pages"):
                            st.write(f"**Страницы:** {', '.join(map(str, res['pages']))}")
                        if res.get("persuasiveness"):
                            st.write(f"**Убедительность:** {res['persuasiveness']}")
                        if res.get("evidence"):
                            st.write(f"**Доказательность:** {res['evidence']}")
            else:
                st.warning("По вашему запросу ничего не найдено")

    elif app_mode == "База знаний":
        st.header("📚 База знаний")

        for disease in planner.knowledge_base["disease"]:
            with st.expander(f"📁 {disease['name']}", expanded=False):
                for type_obj in disease.get("type", []):
                    st.subheader(f"📄 {type_obj['name']} (МКБ-10: {', '.join(type_obj.get('ICD-10_code', []))})")
                    variants = type_obj.get("variant", [])
                    st.write(f"**Вариантов:** {len(variants)}")

                    total_stages = 0
                    total_alt = 0
                    total_joint = 0
                    for v in variants:
                        stages = v.get("stage", [])
                        total_stages += len(stages)
                        for s in stages:
                            alt_groups = s.get("alternative_groups", [])
                            for group in alt_groups:
                                total_alt += len(group.get("surgical methods", []))
                                total_alt += len(group.get("rehabilitation methods", []))
                                total_alt += len(group.get("medicines", []))
                            joint_groups = s.get("joint_groups", [])
                            for group in joint_groups:
                                total_joint += len(group.get("surgical methods", []))
                                total_joint += len(group.get("rehabilitation methods", []))
                                total_joint += len(group.get("medicines", []))

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Вариантов", len(variants))
                    with col2:
                        st.metric("Этапов", total_stages)
                    with col3:
                        st.metric("Альт. методов", total_alt)
                    with col4:
                        st.metric("Совм. методов", total_joint)

                    for v in variants[:3]:
                        st.markdown(f"**{v['name']}**")
                        stages = v.get("stage", [])
                        for s in stages[:2]:
                            alt_count = sum(len(group.get(k, [])) for group in s.get("alternative_groups", []) for k in ["surgical methods", "rehabilitation methods", "medicines"])
                            joint_count = sum(len(group.get(k, [])) for group in s.get("joint_groups", []) for k in ["surgical methods", "rehabilitation methods", "medicines"])
                            st.write(f"  - {s['name_stage']}: {alt_count} альт., {joint_count} совм.")
                    if len(variants) > 3:
                        st.write("  ...")


if __name__ == "__main__":
    main()