import streamlit as st
import pandas as pd
from database import (
    supabase,
    login_school,
    register_school,
    send_password_reset_otp,
    reset_school_password,
    register_new_student
)

# Page configuration
st.set_page_config(page_title="School Fees Portal & Reconciliation", page_icon="🏫", layout="wide")

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "school_id" not in st.session_state:
    st.session_state.school_id = None
if "school_name" not in st.session_state:
    st.session_state.school_name = ""
if "admin_email" not in st.session_state:
    st.session_state.admin_email = ""
if "reset_stage" not in st.session_state:
    st.session_state.reset_stage = "request"  # 'request' or 'verify'
if "sent_otp" not in st.session_state:
    st.session_state.sent_otp = None

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.title("🏫 School Fees Admin & SaaS Portal")
    st.subheader("Automated Reconciliation & Dedicated Virtual Accounts")
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 School Login", "📝 Register New School", "🔑 Forgot Password"])

    # 1. SCHOOL LOGIN
    with auth_tab1:
        st.write("Sign in to access your school workspace.")
        login_email = st.text_input("Admin Email Address", key="login_email")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Log In", type="primary"):
            if not login_email or not login_pass:
                st.error("Please fill in both Email and Password.")
            else:
                res = login_school(login_email, login_pass)
                if res["success"]:
                    school = res["school"]
                    st.session_state.logged_in = True
                    st.session_state.school_id = school["id"]
                    st.session_state.school_name = school["school_name"]
                    st.session_state.admin_email = school["admin_email"]
                    st.success(f"Welcome back, {school['school_name']}!")
                    st.rerun()
                else:
                    st.error(res["message"])

    # 2. REGISTER NEW SCHOOL (For Onboarding & Pitches)
    with auth_tab2:
        st.write("Create a new school portal instantly.")
        reg_name = st.text_input("School Name (e.g., Crown Academy)", key="reg_name")
        reg_email = st.text_input("Official Email Address", key="reg_email")
        reg_pass = st.text_input("Create Password", type="password", key="reg_pass")
        
        if st.button("Create School Account", type="primary"):
            if not reg_name or not reg_email or not reg_pass:
                st.error("All fields are required.")
            else:
                res = register_school(reg_name, reg_email, reg_pass)
                if res["success"]:
                    school = res["school"]
                    st.session_state.logged_in = True
                    st.session_state.school_id = school["id"]
                    st.session_state.school_name = school["school_name"]
                    st.session_state.admin_email = school["admin_email"]
                    st.success("School account created successfully! Redirecting...")
                    st.rerun()
                else:
                    st.error(res["message"])

    # 3. FORGOT PASSWORD FLOW
    with auth_tab3:
        st.write("Reset your account password using email verification.")
        
        if st.session_state.reset_stage == "request":
            reset_email = st.text_input("Enter Registered Admin Email", key="reset_email")
            if st.button("Send Reset OTP"):
                if not reset_email:
                    st.error("Please enter your email.")
                else:
                    with st.spinner("Sending OTP via email..."):
                        res = send_password_reset_otp(reset_email)
                        if res["success"]:
                            st.session_state.sent_otp = res["otp"]
                            st.session_state.admin_email_reset = reset_email.strip().lower()
                            st.session_state.reset_stage = "verify"
                            st.success("OTP sent to your email address!")
                            st.rerun()
                        else:
                            st.error(res["message"])

        elif st.session_state.reset_stage == "verify":
            st.info(f"An OTP was sent to **{st.session_state.admin_email_reset}**")
            entered_otp = st.text_input("Enter 6-Digit OTP Code", key="entered_otp")
            new_pass = st.text_input("Enter New Password", type="password", key="new_pass")
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("Reset Password", type="primary"):
                    if entered_otp.strip() != st.session_state.sent_otp:
                        st.error("Invalid OTP code. Check your email and try again.")
                    elif len(new_pass) < 4:
                        st.error("Password must be at least 4 characters long.")
                    else:
                        res = reset_school_password(st.session_state.admin_email_reset, new_pass)
                        if res["success"]:
                            st.success("Password reset successfully! You can now log in.")
                            st.session_state.reset_stage = "request"
                            st.session_state.sent_otp = None
                        else:
                            st.error(res["message"])
            with col_r2:
                if st.button("Cancel / Back"):
                    st.session_state.reset_stage = "request"
                    st.rerun()

    st.stop()

# --- LOGGED IN SCHOOL DASHBOARD ---

# Sidebar Controls
st.sidebar.title(f"🏫 {st.session_state.school_name}")
st.sidebar.write(f"📧 {st.session_state.admin_email}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.school_id = None
    st.session_state.school_name = ""
    st.session_state.admin_email = ""
    st.rerun()

st.title(f"🏫 {st.session_state.school_name} - Fee Reconciliation Portal")

# Fetch Isolated School Data from Supabase
def load_school_data(school_id):
    students_res = supabase.table("students").select("*").eq("school_id", school_id).execute()
    students_data = students_res.data if students_res.data else []
    
    student_ids = [s["id"] for s in students_data]
    
    if student_ids:
        payments_res = supabase.table("payments").select("*").in_("student_id", student_ids).execute()
        payments_data = payments_res.data if payments_res.data else []
    else:
        payments_data = []

    ledger_res = supabase.table("saas_ledger").select("*").eq("school_id", school_id).execute()
    ledger_data = ledger_res.data if ledger_res.data else []

    return pd.DataFrame(students_data), pd.DataFrame(payments_data), pd.DataFrame(ledger_data)

df_students, df_payments, df_ledger = load_school_data(st.session_state.school_id)

tab1, tab2, tab3 = st.tabs(["📊 Overview & Payments", "➕ Register Student", "💳 SaaS Account & Ledger"])

# --- TAB 1: OVERVIEW & PAYMENTS ---
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Enrolled Students", len(df_students))
    with col2:
        total_collected = df_payments["amount_paid"].sum() if not df_payments.empty else 0
        st.metric("Total Fees Collected", f"₦{total_collected:,.2f}")
    with col3:
        saas_fees = len(df_ledger) * 1000
        st.metric("Reconciliation Fees (₦1,000/pay)", f"₦{saas_fees:,.2f}")
    with col4:
        net_payout = total_collected - saas_fees
        st.metric("Net School Payout", f"₦{net_payout:,.2f}")

    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📋 Real-time Fee Transactions")
        if not df_payments.empty and not df_students.empty:
            df_merged = df_payments.merge(df_students[["id", "student_name"]], left_on="student_id", right_on="id")
            display_df = df_merged[["student_name", "amount_paid", "transaction_reference"]]
            display_df.columns = ["Student", "Amount (₦)", "Reference"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No payment transactions recorded yet.")

    with col_b:
        st.subheader("🎓 Registered Virtual Accounts")
        if not df_students.empty:
            dva_df = df_students[["student_name", "student_class", "account_number", "bank_name"]].copy()
            dva_df["account_number"] = dva_df["account_number"].astype(str)
            dva_df.columns = ["Name", "Class", "Virtual Account", "Bank"]
            st.dataframe(dva_df, use_container_width=True, hide_index=True)
        else:
            st.info("No students registered yet.")

# --- TAB 2: REGISTER NEW STUDENT ---
with tab2:
    st.subheader("➕ Enroll New Student & Generate Dedicated Virtual Account")
    
    with st.form("add_student_form"):
        s_name = st.text_input("Full Student Name")
        s_class = st.text_input("Class (e.g., JSS 1, SS 2)")
        p_phone = st.text_input("Parent Phone Number")
        p_email = st.text_input("Parent Email Address")
        
        submit_student = st.form_submit_button("Generate Virtual Account", type="primary")

    if submit_student:
        if not s_name or not s_class or not p_phone or not p_email:
            st.error("Please complete all student and parent details.")
        else:
            with st.spinner("Communicating with Paystack to allocate Dedicated Account..."):
                res = register_new_student(
                    student_name=s_name,
                    student_class=s_class,
                    parent_phone=p_phone,
                    parent_email=p_email,
                    school_id=st.session_state.school_id
                )
                if res:
                    st.success(f"Virtual Account generated for {s_name}!")
                    st.rerun()
                else:
                    st.error("Failed to generate Virtual Account. Check Paystack credentials.")

# --- TAB 3: SAAS BILLING & LEDGER ---
with tab3:
    st.subheader("💳 SaaS Pay-As-You-Go Billing Model")
    st.write("You only pay **₦1,000 per successful payment transaction**. Zero upfront subscription costs.")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.metric("Total Successful Reconciliations", len(df_ledger))
    with col_l2:
        total_saas_due = len(df_ledger) * 1000
        st.metric("Total SaaS Reconciliation Fees Accrued", f"₦{total_saas_due:,.2f}")

    st.divider()
    if not df_ledger.empty:
        st.subheader("📄 Itemized Transaction Fee Ledger")
        ledger_display = df_ledger[["transaction_reference", "fee_amount", "created_at"]].copy()
        ledger_display.columns = ["Transaction Ref", "Fee Deducted (₦)", "Date Cleared"]
        st.dataframe(ledger_display, use_container_width=True, hide_index=True)
    else:
        st.info("No SaaS transaction fees recorded yet. Fees will appear automatically as parents pay into virtual accounts.")