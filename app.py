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
    st.set_page_config(page_title="AI Code Reviewer", layout="wide")
    st.title("AI Code Review")
    st.write(
        "Paste code or upload a single file below. "
        "An AI will scan your code and generate a review for code accuracy, quality, vulnerabilities, and best practices."
    )


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
        st.caption("This usually takes a couple seconds.")

    if submit_clicked:
        if not source_code.strip():
            st.warning("Please upload a file or paste a code text.")
            return

        try:
            reviewer = load_reviewer()
        except MissingAPIKeyError as exc:
            st.error(str(exc))
            return

        with st.spinner("Generating Review..."):
            try:
                review_markdown, metadata = reviewer.review(
                    source_code,
                    filename=filename,
                )
            except Exception as exc:  # noqa: BLE001 - show any failure to the user
                st.error(f"Review failed: {exc}")
                return

        st.success("Review complete")
        st.markdown(review_markdown)



if __name__ == "__main__":
    main()