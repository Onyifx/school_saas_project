import streamlit as st
import pandas as pd
import urllib.parse
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

# Sidebar Controls & Term Filters
st.sidebar.title(f"🏫 {st.session_state.school_name}")
st.sidebar.write(f"📧 {st.session_state.admin_email}")

st.sidebar.divider()
st.sidebar.subheader("📅 Academic Scope")
selected_session = st.sidebar.selectbox(
    "Academic Session",
    ["2024/2025", "2025/2026", "2026/2027"],
    index=1
)
selected_term = st.sidebar.selectbox(
    "Term",
    ["1st Term", "2nd Term", "3rd Term"],
    index=0
)

st.sidebar.divider()

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.school_id = None
    st.session_state.school_name = ""
    st.session_state.admin_email = ""
    st.rerun()

st.title(f"🏫 {st.session_state.school_name} - Fee Reconciliation Portal")
st.caption(f"Active Scope: **{selected_session} | {selected_term}**")


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

df_students_all, df_payments_all, df_ledger = load_school_data(st.session_state.school_id)


# Filter students by active session and term
if not df_students_all.empty:
    if "academic_session" in df_students_all.columns and "term" in df_students_all.columns:
        df_students = df_students_all[
            (df_students_all["academic_session"] == selected_session) & 
            (df_students_all["term"] == selected_term)
        ]
    else:
        df_students = df_students_all
else:
    df_students = pd.DataFrame()


# Filter payments by active session and term
if not df_payments_all.empty:
    if "academic_session" in df_payments_all.columns and "term" in df_payments_all.columns:
        df_payments = df_payments_all[
            (df_payments_all["academic_session"] == selected_session) & 
            (df_payments_all["term"] == selected_term)
        ]
    else:
        df_payments = df_payments_all
else:
    df_payments = pd.DataFrame()

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
        saas_fees = len(df_payments) * 1000
        st.metric("Reconciliation Fees (₦1,000/pay)", f"₦{saas_fees:,.2f}")
    with col4:
        net_payout = total_collected - saas_fees
        st.metric("Net School Payout", f"₦{net_payout:,.2f}")

    st.divider()
    
    # Render transactions
    st.subheader(f"📋 Real-time Fee Transactions ({selected_session} - {selected_term})")
    if not df_payments.empty and not df_students_all.empty:
        df_merged = df_payments.merge(df_students_all[["id", "student_name"]], left_on="student_id", right_on="id")
        display_df = df_merged[["student_name", "amount_paid", "transaction_reference"]]
        display_df.columns = ["Student", "Amount (₦)", "Reference"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No payment transactions recorded for {selected_session} ({selected_term}).")

    st.divider()

    # Render dynamic balances and WhatsApp link
    st.subheader(f"🎓 Student Balances & Account Sharing ({selected_session} - {selected_term})")
    
    students_res = supabase.table("students").select("*").eq("school_id", st.session_state.school_id).execute()
    students_raw = students_res.data or []
    
    # Filter students list to match selected session & term
    students = [
        s for s in students_raw 
        if s.get("academic_session", "2025/2026") == selected_session and s.get("term", "1st Term") == selected_term
    ]
    
    if students:
        for student in students:
            # Calculate Total Paid for this student in the selected term/session
            payments_res = supabase.table("payments").select("amount_paid, academic_session, term").eq("student_id", student["id"]).execute()
            payments = payments_res.data or []
            
            filtered_payments = [
                p for p in payments 
                if p.get("academic_session", "2025/2026") == selected_session and p.get("term", "1st Term") == selected_term
            ]
            total_paid = sum(p["amount_paid"] for p in filtered_payments) if filtered_payments else 0
            
            expected = student.get("expected_fee") or 0
            balance = expected - total_paid
            parent_phone = student.get("parent_phone") or ""
    
            col_s1, col_s2, col_s3, col_s4 = st.columns([2, 1, 1, 1])
            
            with col_s1:
                st.markdown(f"**{student['student_name']}** ({student['student_class']})<br>🏦 {student['account_number']} ({student['bank_name']})", unsafe_allow_html=True)
            with col_s2:
                st.metric("Total Paid", f"₦{total_paid:,.2f}")
            with col_s3:
                if balance <= 0 and expected > 0:
                    st.success("Fully Paid")
                elif expected == 0:
                    st.info("No fee set")
                else:
                    st.error(f"Owes: ₦{balance:,.2f}")
            with col_s4:
                if parent_phone:
                    clean_phone = parent_phone.strip()
                    if clean_phone.startswith("0"):
                        clean_phone = "234" + clean_phone[1:]
                        
                    msg = f"Dear Parent, please pay {student['student_name']}'s fees for {selected_session} ({selected_term}) into their dedicated account: {student['account_number']} ({student['bank_name']}). Expected: ₦{expected:,.2f}. Outstanding Balance: ₦{balance:,.2f}."
                    encoded_msg = urllib.parse.quote(msg)
                    wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                    
                    st.markdown(f"[📲 Share via WhatsApp]({wa_link})")
                else:
                    st.caption("No Phone Provided")
                    
            st.divider()
    else:
        st.info(f"No students registered for {selected_session} ({selected_term}).")


# --- TAB 2: REGISTER NEW STUDENT ---
with tab2:
    with st.form("register_student_form"):
        st.subheader("Register New Student")
        student_name = st.text_input("Student Full Name")
        student_class = st.selectbox("Class", ["JSS 1", "JSS 2", "JSS 3", "SS 1", "SS 2", "SS 3"])
        parent_phone = st.text_input("Parent Phone Number (e.g., 08030000000)")
        parent_email = st.text_input("Parent Email Address")
        expected_fee = st.number_input("Expected School Fee (₦)", min_value=0.0, step=1000.0)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            reg_session = st.selectbox("Academic Session", ["2024/2025", "2025/2026", "2026/2027"], index=["2024/2025", "2025/2026", "2026/2027"].index(selected_session))
        with col_f2:
            reg_term = st.selectbox("Term", ["1st Term", "2nd Term", "3rd Term"], index=["1st Term", "2nd Term", "3rd Term"].index(selected_term))

        submit = st.form_submit_button("Generate Virtual Account", type="primary")
        
        if submit and student_name and expected_fee > 0:
            with st.spinner("Generating dedicated account..."):
                res = register_new_student(
                    student_name=student_name,
                    student_class=student_class,
                    parent_phone=parent_phone,
                    parent_email=parent_email,
                    school_id=st.session_state.school_id,
                    expected_fee=expected_fee,
                    academic_session=reg_session,
                    term=reg_term
                )
                if res:
                    st.success(f"Virtual Account created for {student_name} ({reg_session} - {reg_term})!")
                    st.rerun()
                else:
                    st.error("Failed to generate account. Check details and try again.")


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