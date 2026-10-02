"""Labeled {query, expected_domain} pairs for measuring routing accuracy.

Target: >= 90% (see Project_Details/05_evaluation_and_testing.md §2). D4, D5 and D6 are
active; D1-D3 are not, so their topics expect UNROUTED -- update those entries to their real
domain once D1-D3 come online.
"""

ROUTING_TEST_SET = [
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
    # Attendance/leave for an event is D6 even though the event itself is co-curricular.
    {"query": "Will I get attendance for a hackathon at another college?", "expected_domain": "D6"},
    {"query": "Do I need HOD permission to miss classes for an inter-college competition?", "expected_domain": "D6"},
    # D4 -- Career, NOC & Placement
    {"query": "What is the eligibility for on-campus placements?", "expected_domain": "D4"},
    {"query": "Why do I need to give a ₹25,000 cheque?", "expected_domain": "D4"},
    {"query": "Which company offers the highest package?", "expected_domain": "D4"},
    {"query": "Can I take another job offer after I'm already placed?", "expected_domain": "D4"},
    {"query": "What is the dress code for placement drives?", "expected_domain": "D4"},
    {"query": "What roles does Meditab offer?", "expected_domain": "D4"},
    # Out of scope while D1-D3 are inactive -- update expected_domain once those domains launch
    {"query": "How do I join the robotics club?", "expected_domain": "UNROUTED"},
    {"query": "What certifications does the college offer in cloud computing?", "expected_domain": "UNROUTED"},
    {"query": "When are the cricket team trials?", "expected_domain": "UNROUTED"},
    {"query": "How do I register for the college hackathon?", "expected_domain": "UNROUTED"},
]
