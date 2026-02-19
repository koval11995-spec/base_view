import streamlit as st
import json
from typing import Dict, List, Optional


class TreatmentPlanner:
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """Инициализация системы планирования лечения"""
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        else:
            self.knowledge_base = {"disease": []}

    def load_knowledge_base(self, filepath: str):
        """Загрузка базы знаний из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.knowledge_base = json.load(f)

    def get_diseases(self) -> List[str]:
        """Получение списка доступных заболеваний"""
        return [disease["name"] for disease in self.knowledge_base["disease"]]

    def get_disease_variants(self, disease_name: str) -> List[Dict]:
        """Получение вариантов заболевания (типов переломов)"""
        for disease in self.knowledge_base["disease"]:
            if disease["name"] == disease_name:
                return disease["type_variant"]
        return []

    def get_patient_groups(self, variant: Dict) -> List[Dict]:
        """
        Получение списка групп пациентов для конкретного варианта.
        Группы хранятся в полях varik1, varik2, ... и содержат описание patients_indications и этапы.
        Возвращает список словарей с ключами: 'id' (имя поля), 'description' (patients_indications), 'data' (полная группа)
        """
        groups = []
        for key, value in variant.items():
            if key.startswith("varik") and isinstance(value, list) and len(value) > 0:
                for idx, group in enumerate(value):
                    groups.append({
                        "id": f"{key}_{idx}",
                        "description": group.get("patients_indications", "Описание отсутствует"),
                        "data": group
                    })
        return groups

    def get_group_plan(self, variant_name: str, group_data: Dict) -> Dict:
        """Получение плана лечения для конкретной группы пациентов."""
        return {
            "variant": variant_name,
            "group_description": group_data.get("patients_indications", ""),
            "stages": group_data.get("stage", [])
        }

    def search_methods_by_keyword(self, keyword: str) -> List[Dict]:
        """Поиск методов лечения по ключевому слову"""
        results = []
        keyword_lower = keyword.lower()

        for disease in self.knowledge_base["disease"]:
            for variant in disease["type_variant"]:
                groups = self.get_patient_groups(variant)
                for group in groups:
                    group_data = group["data"]
                    for stage in group_data.get("stage", []):
                        stage_name = stage["name_stage"]

                        # Поиск в альтернативных методах
                        for alt_method in stage.get("alternative methods", []):
                            if self._method_matches(alt_method, keyword_lower):
                                results.append(self._format_method_result(alt_method, disease, variant, group, stage_name, "alternative"))

                        # Поиск в совместных методах
                        joint = stage.get("joint methods", {})
                        if joint and self._joint_matches(joint, keyword_lower):
                            results.append(self._format_joint_result(joint, disease, variant, group, stage_name))
        return results

    def _method_matches(self, method, keyword_lower):
        """Проверка, содержит ли альтернативный метод ключевое слово"""
        fields_to_check = [
            method.get("name method", ""),
            *method.get("indications", []),
            *method.get("medicines", []),
            *method.get("used material", []),
            method.get("recommendations", "")
        ]
        return any(keyword_lower in str(field).lower() for field in fields_to_check)

    def _joint_matches(self, joint, keyword_lower):
        """Проверка, содержит ли совместный метод ключевое слово (включая вложенные методы)"""
        # Проверяем общие поля
        fields_to_check = [
            *joint.get("indications", []),
            joint.get("recommendations", "")
        ]
        if any(keyword_lower in str(field).lower() for field in fields_to_check):
            return True

        # Проверяем каждый метод внутри блока
        for method in joint.get("methods", []):
            method_fields = [
                method.get("name method", ""),
                *method.get("medicines", []),
                *method.get("used material", [])
            ]
            if any(keyword_lower in str(field).lower() for field in method_fields):
                return True
        return False

    def _format_method_result(self, method, disease, variant, group, stage_name, method_type):
        """Форматирование результата для альтернативного метода"""
        return {
            "method": method.get("name method", "Без названия"),
            "disease": disease["name"],
            "variant": variant["name"],
            "group": group["description"],
            "stage": stage_name,
            "indications": method.get("indications", []),
            "medicines": method.get("medicines", []),
            "materials": method.get("used material", []),
            "recommendations": method.get("recommendations", ""),
            "pages": method.get("pages", []),
            "persuasiveness": method.get("persuasiveness", ""),
            "evidence": method.get("evidence", ""),
            "type": method_type
        }

    def _format_joint_result(self, joint, disease, variant, group, stage_name):
        """Форматирование результата для совместного метода"""
        # Собираем названия всех методов внутри блока
        method_names = [m.get("name method", "Без названия") for m in joint.get("methods", [])]
        methods_str = ", ".join(method_names) if method_names else "Не указаны"
        return {
            "method": f"Совместные методы: {methods_str}",
            "disease": disease["name"],
            "variant": variant["name"],
            "group": group["description"],
            "stage": stage_name,
            "indications": joint.get("indications", []),
            "medicines": [],  # на уровне блока может не быть, но оставим для единообразия
            "materials": [],
            "recommendations": joint.get("recommendations", ""),
            "pages": [],  # страницы обычно указаны внутри каждого метода
            "persuasiveness": "",  # убедительность на уровне блока не задана
            "evidence": "",
            "type": "joint",
            "joint_methods": joint.get("methods", [])  # сохраняем список методов для детального отображения
        }


def main():
    """Основная функция Streamlit приложения"""
    st.set_page_config(
        page_title="Клиническая рекомендация",
        page_icon="🏥",
        layout="wide"
    )

    # Инициализация системы - укажите путь к вашему JSON-файлу
    if 'planner' not in st.session_state:
        json_path = "base7.json"  # замените на актуальный путь
        st.session_state.planner = TreatmentPlanner(json_path)

    planner = st.session_state.planner

    st.title("🏥 Автоматически извлеченная информация из клинической рекомендации")
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

        col1, col2 = st.columns(2)

        with col1:
            diseases = planner.get_diseases()
            if not diseases:
                st.error("База знаний не загружена или пуста. Проверьте путь к файлу.")
                return

            selected_disease = st.selectbox("Выберите заболевание:", diseases)

            if selected_disease:
                variants = planner.get_disease_variants(selected_disease)
                variant_names = [v["name"] for v in variants]

                if variant_names:
                    selected_variant_name = st.selectbox("Выберите тип перелома:", variant_names)
                    selected_variant = next(v for v in variants if v["name"] == selected_variant_name)

                    groups = planner.get_patient_groups(selected_variant)
                    if groups:
                        group_descriptions = [g["description"] for g in groups]
                        selected_group_desc = st.selectbox("Выберите группу пациентов:", group_descriptions)
                        selected_group = next(g for g in groups if g["description"] == selected_group_desc)
                    else:
                        st.warning("Для этого типа перелома нет групп пациентов.")
                        selected_group = None
                else:
                    st.warning("Для этого заболевания нет вариантов.")
                    selected_variant = None
                    selected_group = None

        with col2:
            if selected_variant and selected_group:
                st.subheader("📋 Общая информация")
                st.write(f"**Код МКБ-10:** {selected_variant['ICD-10_code']}")
                if selected_variant.get('general_contraindications'):
                    with st.expander("Общие противопоказания"):
                        for contra in selected_variant['general_contraindications']:
                            st.write(f"• {contra}")

        if selected_variant and selected_group:
            st.markdown("---")
            st.header("📋 План лечения")

            group_plan = planner.get_group_plan(selected_variant["name"], selected_group["data"])

            if group_plan["stages"]:
                tabs = st.tabs([stage["name_stage"] for stage in group_plan["stages"]])

                for i, tab in enumerate(tabs):
                    with tab:
                        stage = group_plan["stages"][i]
                        st.subheader(stage["name_stage"])

                        # Альтернативные методы
                        alt_methods = stage.get("alternative methods", [])
                        if alt_methods:
                            st.markdown("#### Альтернативные методы")
                            for method in alt_methods:
                                with st.expander(f"🔹 {method.get('name method', 'Без названия')}"):
                                    if method.get('indications'):
                                        st.write("**Показания:**")
                                        for ind in method['indications']:
                                            st.write(f"• {ind}")
                                    if method.get('medicines'):
                                        st.write("**Лекарства:**")
                                        for med in method['medicines']:
                                            st.write(f"• {med}")
                                    if method.get('used material'):
                                        st.write("**Материалы:**")
                                        for mat in method['used material']:
                                            st.write(f"• {mat}")
                                    if method.get('recommendations'):
                                        st.write(f"**Рекомендации:** {method['recommendations']}")
                                    if method.get('pages'):
                                        st.write(f"**Страницы:** {', '.join(method['pages'])}")
                                    if method.get('persuasiveness'):
                                        st.write(f"**Убедительность рекомендации:** {method['persuasiveness']}")
                                    if method.get('evidence'):
                                        st.write(f"**Уровень доказательности:** {method['evidence']}")

                        # Совместные методы (обновленная обработка)
                        joint = stage.get("joint methods", {})
                        if joint and joint.get("methods"):
                            st.markdown("#### Совместные методы")
                            # Общие показания и рекомендации для всего блока
                            with st.expander("📌 Общая информация блока"):
                                if joint.get('indications'):
                                    st.write("**Показания для всего блока:**")
                                    for ind in joint['indications']:
                                        st.write(f"• {ind}")
                                if joint.get('recommendations'):
                                    st.write(f"**Общие рекомендации:** {joint['recommendations']}")

                            # Отображаем каждый метод внутри блока
                            for method in joint['methods']:
                                with st.expander(f"🔸 {method.get('name method', 'Без названия')}"):
                                    if method.get('medicines'):
                                        st.write("**Лекарства:**")
                                        for med in method['medicines']:
                                            st.write(f"• {med}")
                                    if method.get('used material'):
                                        st.write("**Материалы:**")
                                        for mat in method['used material']:
                                            st.write(f"• {mat}")
                                    if method.get('pages'):
                                        st.write(f"**Страницы:** {', '.join(method['pages'])}")
                                    if method.get('persuasiveness'):
                                        st.write(f"**Убедительность:** {method['persuasiveness']}")
                                    if method.get('evidence'):
                                        st.write(f"**Доказательность:** {method['evidence']}")

                        if not alt_methods and not joint.get("methods"):
                            st.info("Методы лечения для этого этапа не указаны")
            else:
                st.info("План лечения для этой группы не найден")

            if st.button("📄 Сгенерировать отчет о лечении"):
                generate_treatment_report(group_plan, selected_variant)

    elif app_mode == "Поиск методов":
        st.header("🔍 Поиск методов лечения")

        search_term = st.text_input(
            "Введите ключевое слово для поиска:",
            placeholder="Например: остеосинтез, профилактика, реабилитация..."
        )

        if search_term:
            results = planner.search_methods_by_keyword(search_term)

            if results:
                st.write(f"Найдено результатов: {len(results)}")

                for result in results:
                    with st.expander(f"{result['method']} ({result['disease']} - {result['stage']})"):
                        st.write(f"**Заболевание:** {result['disease']}")
                        st.write(f"**Тип:** {result['variant']}")
                        st.write(f"**Группа:** {result['group']}")
                        st.write(f"**Этап:** {result['stage']}")
                        st.write(f"**Тип метода:** {'Альтернативный' if result['type']=='alternative' else 'Совместный'}")

                        if result['indications']:
                            st.write("**Показания:**")
                            for ind in result['indications']:
                                st.write(f"• {ind}")

                        if result['medicines']:
                            st.write("**Лекарства:**")
                            for med in result['medicines']:
                                st.write(f"• {med}")

                        if result['materials']:
                            st.write("**Материалы:**")
                            for mat in result['materials']:
                                st.write(f"• {mat}")

                        if result.get('recommendations'):
                            st.write(f"**Рекомендации:** {result['recommendations']}")

                        # Для совместных методов показываем также вложенные методы
                        if result['type'] == 'joint' and result.get('joint_methods'):
                            st.write("**Включает методы:**")
                            for m in result['joint_methods']:
                                st.markdown(f"* {m.get('name method', 'Без названия')}")

                        if result.get('pages'):
                            st.write(f"**Страницы:** {', '.join(result['pages'])}")
                        if result.get('persuasiveness'):
                            st.write(f"**Убедительность:** {result['persuasiveness']}")
                        if result.get('evidence'):
                            st.write(f"**Доказательность:** {result['evidence']}")
            else:
                st.warning("По вашему запросу ничего не найдено")

    elif app_mode == "База знаний":
        st.header("📚 База знаний")

        for disease in planner.knowledge_base["disease"]:
            with st.expander(f"📁 {disease['name']}", expanded=True):
                for variant in disease["type_variant"]:
                    st.subheader(f"📄 {variant['name']} (МКБ-10: {variant['ICD-10_code']})")

                    groups = planner.get_patient_groups(variant)
                    if groups:
                        st.write(f"**Групп пациентов:** {len(groups)}")

                        total_stages = 0
                        total_alt_methods = 0
                        total_joint_methods = 0
                        for group in groups:
                            stages = group["data"].get("stage", [])
                            total_stages += len(stages)
                            for stage in stages:
                                total_alt_methods += len(stage.get("alternative methods", []))
                                joint = stage.get("joint methods", {})
                                if joint.get("methods"):
                                    total_joint_methods += len(joint["methods"])

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Групп", len(groups))
                        with col2:
                            st.metric("Всего этапов", total_stages)
                        with col3:
                            st.metric("Альт. методов", total_alt_methods)
                        with col4:
                            st.metric("Совм. методов", total_joint_methods)

                        for group in groups:
                            st.markdown(f"**Группа:** {group['description']}")
                            stages = group["data"].get("stage", [])
                            for stage in stages:
                                alt_count = len(stage.get("alternative methods", []))
                                joint_count = len(stage.get("joint methods", {}).get("methods", []))
                                st.write(f"- {stage['name_stage']}: {alt_count} альт., {joint_count} совм.")
                    else:
                        st.write("Нет групп пациентов")


def generate_treatment_report(group_plan: Dict, variant: Dict):
    """Генерация отчета о лечении"""
    report_text = f"""
# ОТЧЕТ О ПЛАНЕ ЛЕЧЕНИЯ

## Основная информация
**Тип перелома:** {group_plan['variant']}
**Код МКБ-10:** {variant['ICD-10_code']}

## Показания для данной группы
{group_plan['group_description']}

## План лечения
"""

    for stage in group_plan['stages']:
        report_text += f"\n### {stage['name_stage']}\n"

        alt_methods = stage.get("alternative methods", [])
        if alt_methods:
            report_text += "\n**Альтернативные методы:**\n"
            for method in alt_methods:
                report_text += f"\n**{method.get('name method', 'Без названия')}**\n"
                if method.get('indications'):
                    report_text += "Показания:\n" + "\n".join(f"• {ind}" for ind in method['indications']) + "\n"
                if method.get('medicines'):
                    report_text += "Лекарства:\n" + "\n".join(f"• {med}" for med in method['medicines']) + "\n"
                if method.get('used material'):
                    report_text += "Материалы:\n" + "\n".join(f"• {mat}" for mat in method['used material']) + "\n"
                if method.get('recommendations'):
                    report_text += f"Рекомендации: {method['recommendations']}\n"

        joint = stage.get("joint methods", {})
        if joint and joint.get("methods"):
            report_text += "\n**Совместные методы:**\n"
            if joint.get('indications'):
                report_text += "Общие показания:\n" + "\n".join(f"• {ind}" for ind in joint['indications']) + "\n"
            if joint.get('recommendations'):
                report_text += f"Общие рекомендации: {joint['recommendations']}\n"
            for method in joint['methods']:
                report_text += f"\n* {method.get('name method', 'Без названия')}\n"
                if method.get('medicines'):
                    report_text += "  Лекарства: " + ", ".join(method['medicines']) + "\n"
                if method.get('used material'):
                    report_text += "  Материалы: " + ", ".join(method['used material']) + "\n"

    st.markdown("---")
    st.header("📄 Сгенерированный отчет")
    st.markdown(report_text)

    st.download_button(
        label="📥 Скачать отчет",
        data=report_text,
        file_name=f"treatment_plan_{group_plan['variant'].replace(' ', '_')}.md",
        mime="text/markdown"
    )


if __name__ == "__main__":
    main()