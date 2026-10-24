"""Labeled {query, expected_domain} pairs for measuring routing accuracy.

Target: >= 90% (see Project_Details/05_evaluation_and_testing.md §2). All six domains are active;
UNROUTED cases are questions outside every domain.
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
]
