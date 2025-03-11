import streamlit as st
import json
import re
import io
import pandas as pd
from typing import Union

# ----- Defaults and helper functions -----
DEFAULT_COUNT = 1
DEFAULT_TITLE = ""
DEFAULT_CARD_ELEMENTS = """fill | 1
text | {{Description}}
fill | 1"""
DEFAULT_TAGS = ""
DEFAULT_COLOR = "#0000FF"  # Blue
DEFAULT_TITLE_SIZE = 13
DEFAULT_CARD_FONT_SIZE = 12
DEFAULT_ICON = ""
DEFAULT_VARIABLE_COLOR = False

def generate_template_from_form():
    count = st.session_state.get("count", DEFAULT_COUNT)
    title = st.session_state.get("title", DEFAULT_TITLE)
    card_elements = st.session_state.get("card_elements", DEFAULT_CARD_ELEMENTS)
    tags = st.session_state.get("tags", DEFAULT_TAGS)
    color = st.session_state.get("color", DEFAULT_COLOR)
    variable_color = st.session_state.get("variable_color", DEFAULT_VARIABLE_COLOR)
    title_size = st.session_state.get("title_size", DEFAULT_TITLE_SIZE)
    card_font_size = st.session_state.get("card_font_size", DEFAULT_CARD_FONT_SIZE)
    icon = st.session_state.get("icon", DEFAULT_ICON)
    
    template = {
        "count": count if count > 0 else "{{Count}}",
        "title": title.strip() or "{{Title}}",
        "contents": [line for line in card_elements.splitlines() if line.strip()],
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "color": color if not variable_color else "{{Color}}",
        "title_size": str(title_size),
        "card_font_size": str(card_font_size),
        "icon": icon.strip() or "{{Icon}}"
    }
    return template

# ----- Initialize session_state defaults if not present -----
if "count" not in st.session_state:
    st.session_state.count = DEFAULT_COUNT
if "title" not in st.session_state:
    st.session_state.title = DEFAULT_TITLE
if "card_elements" not in st.session_state:
    st.session_state.card_elements = DEFAULT_CARD_ELEMENTS
if "tags" not in st.session_state:
    st.session_state.tags = DEFAULT_TAGS
if "variable_color" not in st.session_state:
    st.session_state.variable_color = DEFAULT_VARIABLE_COLOR
if "color" not in st.session_state:
    st.session_state.color = DEFAULT_COLOR
if "title_size" not in st.session_state:
    st.session_state.title_size = DEFAULT_TITLE_SIZE
if "card_font_size" not in st.session_state:
    st.session_state.card_font_size = DEFAULT_CARD_FONT_SIZE
if "icon" not in st.session_state:
    st.session_state.icon = DEFAULT_ICON
if "template_json" not in st.session_state:
    st.session_state.template_json = json.dumps(generate_template_from_form(), indent=2)

def validate_template(template_text: str) -> Union[bool,str|None]:
    try:
        json.loads(template_text)
        return True, None
    except json.JSONDecodeError as e:
        return False, str(e)

def extract_fields(template_text) -> list[dict]:
    # Auto-detect fields from placeholders like {{FieldName}}
    return list(dict.fromkeys(re.findall(r"{{(.*?)}}", template_text)))

def merge_template(template: str, row) -> str:
    merged = template
    for key, value in row.items():
        merged = merged.replace(f"{{{{{key}}}}}", str(value))
    return merged

def preview_component(template_text: str, data: pd.DataFrame) -> None:
    st.subheader("Auto-updated Preview")
    preview = []
    for idx, row in data.iterrows():
        merged_str = merge_template(template_text, row)
        try:
            merged_obj = json.loads(merged_str)
            preview.append(merged_obj)
        except Exception:
            continue
    st.json(preview)

@st.dialog("Paste CSV Data")
def paste_csv_data(fields):
    paste_text = st.text_area("Paste your data here (CSV or tab-delimited):", height=150)
    if st.button("Load Data", key="load_data_button"):
        try:
            sep = "\t" if "\t" in paste_text else ","
            st.session_state.data_df = pd.read_csv(
                io.StringIO(paste_text),
                sep=sep,
                header=None,
                names=fields
            )
            st.rerun()
        except Exception as e:
            st.error(f"Error parsing data: {e}")

def merge_dataframe_fields(old_df, new_fields):
    """Merge old_df with new_fields:
       - Preserve data for columns present in both.
       - Add new columns with empty strings.
    """
    # If no existing rows, just return an empty DataFrame with new columns.
    if old_df.empty:
        return pd.DataFrame(columns=new_fields)
    
    # Create a new DataFrame with the same index as old_df and new columns.
    new_df = pd.DataFrame(index=old_df.index, columns=new_fields)
    
    for col in new_fields:
        if col in old_df.columns:
            new_df[col] = old_df[col]
        else:
            new_df[col] = ""  # Or use NaN if preferred
    return new_df

def main():
    st.set_page_config(
        page_title="RPG Card Generator",
        page_icon=":material/cards:",
        layout="wide"
    )
    st.title("RPG Card Generator")
    
    st.subheader("Template Setup")
    col1, col2 = st.columns(2)
    with col1:
        st.text_area("Card Elements (each line will be an element)", height=300, key="card_elements")
        st.markdown("[See here for more information](https://crobi.github.io/rpg-cards/)")
        # Display detected fields from card elements.
        st.markdown(f"**Fields**: {', '.join(list(dict.fromkeys(re.findall(r'{{(.*?)}}', st.session_state.card_elements))))}")
    with col2:
        st.number_input("Count (0 becomes variable)", min_value=0, key="count")
        st.text_input("Title (blank becomes variable)", key="title")
        st.text_input("Tags (comma separated)", key="tags")
        variable_color = st.checkbox("Variable Color", key="variable_color", value=st.session_state.variable_color)
        if not variable_color:
            st.color_picker("Color", key="color")
        st.number_input("Title Size", key="title_size", step=1)
        st.number_input("Card Font Size", key="card_font_size", step=1)
        st.text_input("Icon (blank becomes variable)", key="icon")

    
    template = generate_template_from_form()
    st.session_state.template_json = json.dumps(template, indent=2)
    
    valid, error_msg = validate_template(st.session_state.template_json)
    if not valid:
        st.error(f"Invalid JSON: {error_msg}")
        st.stop()
    
    # Auto-detect fields from the template
    fields = extract_fields(st.session_state.template_json)
    # Check if fields have changed.
    if "fields" not in st.session_state:
        st.session_state.fields = fields
        st.session_state.data_df = pd.DataFrame(columns=fields)
    elif st.session_state.fields != fields:
        st.session_state.data_df = merge_dataframe_fields(st.session_state.data_df, fields)
        st.session_state.fields = fields
    # st.write("Detected fields:", fields)
    
    st.subheader("Data Entry")
    # Button to open the paste modal
    if st.button("Paste CSV Data", icon=":material/content_paste:"):
        paste_csv_data(fields)

    # Create an empty DataFrame with auto-detected columns
    data = st.data_editor(
        st.session_state.data_df,
        num_rows="dynamic",
        use_container_width=True
    )

    merged_data = []
    for idx, row in data.iterrows():
        merged_str = merge_template(st.session_state.template_json, row)
        try:
            merged_obj = json.loads(merged_str)
            merged_data.append(merged_obj)
        except Exception as e:
            st.error(f"Error in row {idx}: {e}")
    
    st.subheader("Generate")
    st.download_button(
        "Download JSON",
        data=json.dumps(merged_data, indent=2),
        file_name="rpg-cards.json",
        icon=":material/file_download:",
        type="primary"
    )

    st.divider()

    st.subheader("Debug")

    if st.button("Debug", icon=":material/bug_report:"):
        st.code(st.session_state.template_json)
    
    # 

if __name__ == "__main__":
    main()
