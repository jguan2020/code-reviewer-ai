import streamlit as st

from reviewer import CodeReviewService, MissingAPIKeyError, get_reviewer


@st.cache_resource(show_spinner=False)
def load_reviewer() -> CodeReviewService:
    return get_reviewer()


def read_uploaded_file(uploaded_file) -> str:
    data = uploaded_file.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore")


def main():
    st.set_page_config(page_title="LLM Code Reviewer", layout="wide")
    st.title("Claude-Powered Code Reviewer")
    st.write(
        "Paste code or upload a single file below, then let Claude 3.5 Sonnet produce a focused review. "
        "Nothing is stored on the server beyond the single request."
    )

    with st.sidebar:
        st.header("Review Settings")
        language = st.text_input("Language hint (optional)")
        notes = st.text_area("Additional context for Claude (optional)", height=120)

    uploaded_file = st.file_uploader("Upload a code file", type=None)
    pasted_code = st.text_area("Or paste code directly", height=320, placeholder="def hello_world():\n    print('Hello!')\n")

    source_code = ""
    filename = None
    if uploaded_file is not None:
        filename = uploaded_file.name
        source_code = read_uploaded_file(uploaded_file)
    elif pasted_code.strip():
        source_code = pasted_code

    col1, col2 = st.columns([1, 3])
    with col1:
        submit_clicked = st.button("Review", use_container_width=True)
    with col2:
        st.caption("Claude responses usually take a few seconds. Larger files can take longer due to token limits.")

    if submit_clicked:
        if not source_code.strip():
            st.warning("Please upload a file or paste code before requesting a review.")
            return

        try:
            reviewer = load_reviewer()
        except MissingAPIKeyError as exc:
            st.error(str(exc))
            return

        with st.spinner("Requesting review from Claude 3.5 Sonnet..."):
            try:
                review_markdown, metadata = reviewer.review(
                    source_code,
                    filename=filename,
                    language=language,
                    notes=notes,
                )
            except Exception as exc:  # noqa: BLE001 - show any failure to the user
                st.error(f"Review failed: {exc}")
                return

        st.success("Review complete")
        st.markdown(review_markdown)

        st.caption(
            f"Model `{metadata.model}` • Input tokens: {metadata.input_tokens} • Output tokens: {metadata.output_tokens}"
        )


if __name__ == "__main__":
    main()