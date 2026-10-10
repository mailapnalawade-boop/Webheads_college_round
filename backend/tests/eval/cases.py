"""Labeled evaluation cases: (tag, source, claim, expected, expected_error_text).

expected is SUPPORTED, CONTRADICTED, or UNCERTAIN (= INSUFFICIENT_EVIDENCE or AMBIGUOUS: flagged, never an error).
expected_error_text (optional) is the exact words of the claim that are wrong. None of these cases were used
to build or tune the judge.
"""
S, C, U = "SUPPORTED", "CONTRADICTED", "UNCERTAIN"

CASES = [
    # ---- swapped numbers / quantities
    ("numeric", "The trial enrolled 150 participants across three sites.", "The trial enrolled 200 participants.", C, "200"),
    ("numeric", "The bridge is 1,200 metres long.", "The bridge is 1,800 metres long.", C, "1,800 metres"),
    ("numeric", "Adults should take 500mg of the drug three times daily.", "Adults should take 50mg of the drug three times daily.", C, "50mg"),
    ("numeric", "The company reported revenue of 45 million dollars.", "The company reported revenue of 54 million dollars.", C, "54 million dollars"),
    ("numeric", "Inflation was 6.2% in March.", "Inflation was 2.6% in March.", C, "2.6%"),
    ("numeric", "The warranty covers 24 months.", "The warranty covers 12 months.", C, "12 months"),
    ("numeric", "The tower is 324 metres tall.", "The tower is 424 metres tall.", C, "424 metres"),
    ("numeric", "The vaccine is 95% effective in adults.", "The vaccine is 59% effective in adults.", C, "59%"),
    # ---- years / dates
    ("year", "The Eiffel Tower was completed in 1889.", "The Eiffel Tower was completed in 1899.", C, "1899"),
    ("year", "The company was founded in 2004 in Pune.", "The company was founded in 2014 in Pune.", C, "2014"),
    ("year", "The law came into force in 2019.", "The law came into force in 2021.", C, "2021"),
    ("year", "Construction began in 1931 and ended in 1936.", "Construction began in 1931.", S, None),
    # ---- frequency
    ("frequency", "The drug is taken once daily with food.", "The drug is taken twice daily with food.", C, "twice"),
    ("frequency", "Take the tablet three times daily after meals.", "Take the tablet once daily after meals.", C, "once"),
    ("frequency", "The pump is serviced twice a year.", "The pump is serviced twice a year.", S, None),
    # ---- names / places / people
    ("entity", "The treaty was signed in Vienna in 1815.", "The treaty was signed in Geneva.", C, "Geneva"),
    ("entity", "The project was led by Dr. Rao at the institute.", "The project was led by Dr. Mehta at the institute.", C, "Mehta"),
    ("entity", "The capital of Australia is Canberra.", "The capital of Australia is Sydney.", C, "Sydney"),
    ("entity", "The report was written by Priya Nair for the ministry.", "The report was written by Anita Desai for the ministry.", C, "Anita Desai"),
    ("entity", "The conference took place in Mumbai last March.", "The conference took place in Chennai last March.", C, "Chennai"),
    ("entity", "Marie Curie won the Nobel Prize in Physics in 1903.", "Marie Curie won the Nobel Prize in Physics.", S, None),
    ("entity", "The merger was approved by the Competition Commission.", "The merger was approved by the Competition Commission.", S, None),
    ("entity", "Paris is the capital of France. Berlin is the capital of Germany.", "Paris is the capital of Germany.", C, "Germany"),
    # ---- equal values written differently (must NOT be flagged)
    ("equivalent", "The dose is 50 mg once daily.", "The dose is 0.05 g once daily.", S, None),
    ("equivalent", "Revenue was $5,000,000 in the quarter.", "Revenue was 5 million dollars in the quarter.", S, None),
    ("equivalent", "The recommended dose is 500mg to 1000mg three times daily.", "The recommended dose is 750mg three times daily.", S, None),
    ("equivalent", "Water boils at 100 degrees Celsius at sea level.", "At sea level, water boils at 100 degrees Celsius.", S, None),
    # ---- different situation, not an error
    ("context", "Revenue was 7 million dollars in 2023.", "Revenue was 5 million dollars in 2022.", U, None),
    ("context", "Dr. Jones reported 150 cases in the northern district.", "Dr. Smith reported 90 cases in the southern district.", U, None),
    ("context", "The 2019 survey covered 1,000 households.", "The 2023 survey covered 3,000 households.", U, None),
    # ---- meaning reversals with no number/name change (need the NLI model)
    ("reversal", "Sales fell sharply last quarter.", "Sales grew strongly last quarter.", C, None),
    ("reversal", "The budget was decreased due to spending constraints.", "The budget was increased due to spending constraints.", C, None),
    ("reversal", "The committee rejected the proposal.", "The committee approved the proposal.", C, None),
    ("reversal", "Aspirin should not be given to children with viral infections.", "Aspirin is recommended for children with viral infections.", C, None),
    ("reversal", "The flight arrived early.", "The flight arrived late.", C, None),
    ("reversal", "Unemployment rose over the year.", "Unemployment declined over the year.", C, None),
    ("reversal", "The patch makes the system slower.", "The patch makes the system faster.", C, None),
    ("reversal", "The company acquired the startup.", "The startup acquired the company.", C, None),
    # ---- negation
    ("negation", "The patient has no history of diabetes.", "The patient has a history of diabetes.", C, None),
    ("negation", "The drug is effective in children.", "The drug is not effective in children.", C, None),
    ("negation", "The audit found irregularities in the accounts.", "The audit found no irregularities in the accounts.", C, None),
    ("negation", "The drug is safe when taken as directed.", "The drug is not harmful when taken as directed.", S, None),
    ("negation", "The device is not waterproof.", "The device is not waterproof.", S, None),
    # ---- correct paraphrases (need the NLI model to be confirmed)
    ("paraphrase", "Sleep is important for our body.", "Sleep is essential for our body.", S, None),
    ("paraphrase", "Revenue increased by 10 percent compared with last year.", "Revenue grew by 10% year over year.", S, None),
    ("paraphrase", "The CEO resigned in January.", "The chief executive stepped down in January.", S, None),
    ("paraphrase", "Regular exercise lowers the risk of heart disease.", "Exercising regularly reduces heart disease risk.", S, None),
    ("paraphrase", "The car broke down on the highway.", "The automobile stopped working on the motorway.", S, None),
    ("paraphrase", "Smoking causes lung cancer.", "Lung cancer is caused by smoking.", S, None),
    ("paraphrase", "The museum is closed on Mondays.", "The museum does not open on Mondays.", S, None),
    ("paraphrase", "Employees must submit expense reports within 30 days.", "Expense reports have to be submitted by employees within 30 days.", S, None),
    # ---- verbatim / near-verbatim correct
    ("verbatim", "The study found that coffee intake was unrelated to sleep duration.", "The study found that coffee intake was unrelated to sleep duration.", S, None),
    ("verbatim", "Proper sleep helps improve memory and concentration.", "Proper sleep helps improve memory and concentration.", S, None),
    ("verbatim", "The new policy takes effect on 1 April 2025.", "The new policy takes effect on 1 April 2025.", S, None),
    ("verbatim", "Lack of sleep can cause tiredness and difficulty concentrating.", "Lack of sleep can cause tiredness and difficulty concentrating.", S, None),
    # ---- unsupported: source silent on the claim
    ("unsupported", "The company published its annual infrastructure report.", "The company plans to open an office in Lisbon.", U, None),
    ("unsupported", "The museum is closed on Mondays.", "The museum charges 20 dollars for entry.", U, None),
    ("unsupported", "The drug reduces blood pressure in adults.", "The drug is manufactured in Hyderabad.", U, None),
    ("unsupported", "The bridge was designed by a local firm.", "The bridge won an international design award.", U, None),
    ("unsupported", "Sleep is important for health.", "Using a phone before bed always improves sleep quality.", U, None),
    ("unsupported", "The survey covered urban households.", "Most respondents preferred online shopping.", U, None),
    ("unsupported", "The CEO announced the results on Tuesday.", "The company intends to hire 500 engineers.", U, None),
    ("unsupported", "The reservoir supplies water to the eastern district.", "The reservoir was built by the British.", U, None),
    # ---- partial / ambiguous
    ("partial", "The preliminary project outline was drafted in late 2025.", "The project launched in quarter 4 of 2025.", U, None),
    ("partial", "Initial results look promising but are not yet conclusive.", "The treatment is proven to work.", U, None),
    ("partial", "The minister said talks were continuing.", "The agreement was finalised.", U, None),
    ("partial", "Some studies link the additive to headaches.", "The additive causes headaches.", U, None),
]
