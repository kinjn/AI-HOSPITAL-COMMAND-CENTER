"""Custom fluid navigation bar component for the AI Hospital Command Center."""

import streamlit as st


def render_navbar(active_page: str) -> None:
    """Renders the custom top navigation bar and hides the default Streamlit sidebar menu.

    Args:
        active_page: The key of the active page ('nav_home', 'nav_intake', 'nav_dashboard', 'nav_detail').
    """
    # Global CSS injection to hide default page navigation and style our custom buttons
    st.markdown(
        """
        <style>
            /* Hide the default Streamlit sidebar completely */
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            
            /* Add spacing at the top of the main container */
            .block-container {
                padding-top: 2rem !important;
            }

            /* Custom navbar container styling */
            .custom-nav-container {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
                padding: 12px 24px;
                margin-bottom: 28px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
            
            /* Styling for navbar buttons */
            div.st-key-nav_home button,
            div.st-key-nav_intake button,
            div.st-key-nav_dashboard button,
            div.st-key-nav_detail button {
                background-color: #F9FAFB !important;
                color: #4B5563 !important;
                border: 1px solid #E5E7EB !important;
                border-radius: 20px !important;
                padding: 6px 16px !important;
                font-weight: 500 !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
                width: 100% !important;
                height: 42px !important;
                font-size: 0.95rem !important;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
            }

            /* Hover states with micro-animations */
            div.st-key-nav_home button:hover,
            div.st-key-nav_intake button:hover,
            div.st-key-nav_dashboard button:hover,
            div.st-key-nav_detail button:hover {
                background-color: #EEF2F6 !important;
                color: #4F46E5 !important;
                border-color: #C7D2FE !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.1), 0 2px 4px -1px rgba(79, 70, 229, 0.06) !important;
            }

            /* Click action micro-movement */
            div.st-key-nav_home button:active,
            div.st-key-nav_intake button:active,
            div.st-key-nav_dashboard button:active,
            div.st-key-nav_detail button:active {
                transform: translateY(0px) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Style the active page button
    st.markdown(
        f"""
        <style>
            div.st-key-{active_page} button {{
                background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
                color: #FFFFFF !important;
                border-color: #4F46E5 !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 10px rgba(79, 70, 229, 0.3) !important;
            }}
            div.st-key-{active_page} button:hover {{
                color: #FFFFFF !important;
                border-color: #3730A3 !important;
                background: linear-gradient(135deg, #4338CA 0%, #312E81 100%) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Navbar columns: Brand column takes larger space, followed by button columns
    cols = st.columns([3.2, 1.2, 1.5, 1.6, 1.5, 0.5])

    # 1. Branding (Logo & App Name)
    with cols[0]:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 12px; height: 42px;">
                <div style="background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%); 
                            padding: 6px 12px; border-radius: 10px; font-weight: 800; 
                            color: white; font-size: 1rem; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.25);
                            display: flex; align-items: center; justify-content: center; height: 32px;">
                    🏥 AI-HCC
                </div>
                <div style="display: flex; flex-direction: column; justify-content: center;">
                    <span style="font-weight: 700; color: #1F2937; font-size: 1.15rem; line-height: 1.1;">
                        Hospital Command Center
                    </span>
                    <span style="font-size: 0.72rem; color: #6B7280; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-top: 1px;">
                        Patient Flow Dashboard
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Navigation items
    pages = [
        {"name": "Home", "icon": "🏠", "key": "nav_home", "file": "app.py"},
        {"name": "Symptom Intake", "icon": "📝", "key": "nav_intake", "file": "pages/intake.py"},
        {"name": "Ops Dashboard", "icon": "📊", "key": "nav_dashboard", "file": "pages/dashboard.py"},
        {"name": "Encounter Details", "icon": "🩺", "key": "nav_detail", "file": "pages/encounter_detail.py"},
    ]

    for idx, page in enumerate(pages):
        with cols[idx + 1]:
            if st.button(f"{page['icon']}  {page['name']}", key=page["key"]):
                st.switch_page(page["file"])

    # Separation divider
    st.markdown(
        "<hr style='margin-top: 12px; margin-bottom: 24px; border: 0; border-top: 1px solid #E5E7EB;' />",
        unsafe_allow_html=True,
    )
