"""Labeled {query, expected_domain} pairs for measuring routing accuracy.

Target: >= 90% (see Project_Details/05_evaluation_and_testing.md §2). All six domains are active;
UNROUTED cases are questions outside every domain.

Optional "kind" groups the harder cases so their accuracy is reported separately (cases without
one are "basic"): qa-regression, overlap, typo, hinglish, gujarati, request, out-of-scope. The basic
cases are clean and phrased like the documents, so on their own they hid real misroutes (QRO-14).
"""

ROUTING_TEST_SET = [
    # D1 -- Clubs, NSS & NCC
    {"query": "How do I join the robotics club?", "expected_domain": "D1"},
    {"query": "Who are the faculty coordinators of the AI/ML Club?", "expected_domain": "D1"},
    {"query": "What is the website of the Competitive Programming Squad?", "expected_domain": "D1"},
    {"query": "Who is the NSS Program Officer for CSPIT CE?", "expected_domain": "D1"},
    {"query": "What are the benefits of joining NCC?", "expected_domain": "D1"},
    {"query": "Which clubs organise hackathons?", "expected_domain": "D1"},
    # D2 -- Certifications
    {"query": "What certifications does the college offer in cloud computing?", "expected_domain": "D2"},
    {"query": "Which AWS certification should I start with?", "expected_domain": "D2"},
    {"query": "How much does the CCNA exam cost?", "expected_domain": "D2"},
    {"query": "What student discounts are available for certifications?", "expected_domain": "D2"},
    {"query": "Which certifications should I do to become a cloud engineer?", "expected_domain": "D2"},
    # D3 -- Extra-curricular Activities & Sports
    {"query": "When are the cricket team trials?", "expected_domain": "D3"},
    {"query": "Who is the faculty coordinator for boys cricket in Spoural?", "expected_domain": "D3"},
    {"query": "Which cultural events are there in Spoural?", "expected_domain": "D3"},
    {"query": "Is there e-sports for girls?", "expected_domain": "D3"},
    # D5 -- Formal Education
    {"query": "How many electives can I choose this semester?", "expected_domain": "D5"},
    {"query": "What is the syllabus for the data structures course?", "expected_domain": "D5"},
    {"query": "Can I switch to a different elective after the semester starts?", "expected_domain": "D5"},
    {"query": "Who do I contact about updating the academic regulations?", "expected_domain": "D5"},
    {"query": "What is the process for choosing an open elective?", "expected_domain": "D5"},
    {"query": "Is there a minor in AI offered this year?", "expected_domain": "D5"},
    {"query": "What is the last date to pay fees and what is the late fine?", "expected_domain": "D5"},
    # D6 -- Leave Management & Attendance
    {"query": "How many days of leave am I eligible for this semester?", "expected_domain": "D6"},
    {"query": "What happens if my attendance falls below 75%?", "expected_domain": "D6"},
    {"query": "How do I apply for condonation of attendance shortage?", "expected_domain": "D6"},
    {"query": "What documents do I need to submit a medical leave application?", "expected_domain": "D6"},
    {"query": "Is there a limit on how many leaves I can take in a semester?", "expected_domain": "D6"},
    {"query": "Who approves a leave request for more than a week?", "expected_domain": "D6"},
    # Attendance/leave for an event is D6 even though the event itself belongs to clubs/sports.
    {"query": "Will I get attendance for a hackathon at another college?", "expected_domain": "D6"},
    {"query": "Do I need HOD permission to miss classes for an inter-college competition?", "expected_domain": "D6"},
    # D4 -- Career, NOC & Placement
    {"query": "What is the eligibility for on-campus placements?", "expected_domain": "D4"},
    {"query": "Why do I need to give a ₹25,000 cheque?", "expected_domain": "D4"},
    {"query": "Which company offers the highest package?", "expected_domain": "D4"},
    {"query": "Can I take another job offer after I'm already placed?", "expected_domain": "D4"},
    {"query": "What is the dress code for placement drives?", "expected_domain": "D4"},
    {"query": "What roles does Meditab offer?", "expected_domain": "D4"},
    # Outside every domain
    {"query": "Who won the IPL last year?", "expected_domain": "UNROUTED"},
    {"query": "Can you recommend a good laptop for coding?", "expected_domain": "UNROUTED"},
    {"query": "What is on the hostel mess menu today?", "expected_domain": "UNROUTED"},
    # --- Misroutes found by the 2026-10-31 QA pass ---
    # QRO-04: the Rs. 300 cheque-bounce penalty is in FeesStructure (D5); routed UNROUTED at 1.0.
    {"query": "What is the penalty if my fee cheque bounces?", "expected_domain": "D5", "kind": "qa-regression"},
    # QRO-05: 80% attendance in placement activities is a placement rule; flipped D4/D6.
    {"query": "What is the minimum attendance needed for placement eligibility?", "expected_domain": "D4", "kind": "qa-regression"},
    {"query": "What documents do I need for an NOC?", "expected_domain": "D4", "kind": "qa-regression"},
    {"query": "What is the NOC process for doing an internship?", "expected_domain": "D4", "kind": "qa-regression"},
    {"query": "What is the fee for 3rd year mechanical NRI?", "expected_domain": "D5", "kind": "qa-regression"},
    {"query": "Can I take a self-sourced offer after I'm already placed through CDPC?", "expected_domain": "D4", "kind": "qa-regression"},
    # --- Overlapping topics: the label is where the answer lives ---
    # Placement vs attendance
    {"query": "Will skipping the FOHSS training sessions affect my placement eligibility?", "expected_domain": "D4", "kind": "overlap"},
    {"query": "Is attendance given for days I spend at placement drives?", "expected_domain": "D6", "kind": "overlap"},
    {"query": "Do parents have to meet the HOD if my attendance is low?", "expected_domain": "D6", "kind": "overlap"},
    {"query": "Does low attendance in placement training stop me from sitting for drives?", "expected_domain": "D4", "kind": "overlap"},
    # NCC / NSS vs leave
    {"query": "Do I get leave for the NCC camp?", "expected_domain": "D6", "kind": "overlap"},
    {"query": "What happens at the NCC annual training camp?", "expected_domain": "D1", "kind": "overlap"},
    {"query": "Can I miss classes to attend an NSS special camp?", "expected_domain": "D6", "kind": "overlap"},
    {"query": "How many NSS units does CHARUSAT have?", "expected_domain": "D1", "kind": "overlap"},
    # Sports vs scholarships vs attendance
    {"query": "Are there scholarships for state-level sports players?", "expected_domain": "D5", "kind": "overlap"},
    {"query": "Who is the faculty coordinator for football in Spoural?", "expected_domain": "D3", "kind": "overlap"},
    {"query": "Do I get attendance for playing in a university-level tournament?", "expected_domain": "D6", "kind": "overlap"},
    # Fee cheque vs placement security-deposit cheque
    {"query": "What happens to my 25,000 cheque if I refuse a placement offer?", "expected_domain": "D4", "kind": "overlap"},
    {"query": "What is the late fine for paying the semester fee after the due date?", "expected_domain": "D5", "kind": "overlap"},
    # Clubs vs certifications vs electives
    {"query": "Which club helps students prepare for AWS?", "expected_domain": "D1", "kind": "overlap"},
    {"query": "How much does the AWS Cloud Practitioner exam cost?", "expected_domain": "D2", "kind": "overlap"},
    {"query": "Is there a cloud computing elective in semester 5?", "expected_domain": "D5", "kind": "overlap"},
    {"query": "Which certifications help me get placed in cloud roles?", "expected_domain": "D2", "kind": "overlap"},
    {"query": "Which companies hire for cloud roles through campus placement?", "expected_domain": "D4", "kind": "overlap"},
    # --- Typos ---
    {"query": "wat is the minimum attendence requirment", "expected_domain": "D6", "kind": "typo"},
    {"query": "placment eligiblity criteria", "expected_domain": "D4", "kind": "typo"},
    {"query": "sylabus for data structres", "expected_domain": "D5", "kind": "typo"},
    {"query": "nss programe officer for cspit", "expected_domain": "D1", "kind": "typo"},
    {"query": "aws certfication exam cost", "expected_domain": "D2", "kind": "typo"},
    {"query": "cricket cordinator in spoural", "expected_domain": "D3", "kind": "typo"},
    # --- Hinglish ---
    {"query": "medical leave kaise apply kare?", "expected_domain": "D6", "kind": "hinglish"},
    {"query": "sem 5 ke electives kaun se hai?", "expected_domain": "D5", "kind": "hinglish"},
    {"query": "NCC join karne ke kya fayde hai?", "expected_domain": "D1", "kind": "hinglish"},
    {"query": "fees kab tak bharni hai?", "expected_domain": "D5", "kind": "hinglish"},
    {"query": "Spoural mein kaun kaun se sports hai?", "expected_domain": "D3", "kind": "hinglish"},
    {"query": "cloud ke liye konsa certification karu?", "expected_domain": "D2", "kind": "hinglish"},
    {"query": "placement ke liye 25000 ka cheque kyu dena padta hai?", "expected_domain": "D4", "kind": "hinglish"},
    # --- Gujarati ---
    {"query": "હાજરી ઓછી હોય તો શું થાય?", "expected_domain": "D6", "kind": "gujarati"},  # low attendance
    {"query": "પ્લેસમેન્ટ માટે લાયકાત શું છે?", "expected_domain": "D4", "kind": "gujarati"},  # placement eligibility
    # --- Status and action requests: still routed, so the reply names the right contact ---
    {"query": "Has my leave been approved?", "expected_domain": "D6", "kind": "request"},
    {"query": "What's the status of my NOC application?", "expected_domain": "D4", "kind": "request"},
    {"query": "Register me for the Meditab placement drive", "expected_domain": "D4", "kind": "request"},
    {"query": "Mark me present for yesterday's lecture", "expected_domain": "D6", "kind": "request"},
    # --- Outside every domain ---
    {"query": "What's the weather in Anand today?", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
    {"query": "Write a Python program to reverse a string", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
    {"query": "Who is the Prime Minister of India?", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
    {"query": "What time does the central library open?", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
    {"query": "How do I reset my college email password?", "expected_domain": "UNROUTED", "kind": "out-of-scope"},
]
