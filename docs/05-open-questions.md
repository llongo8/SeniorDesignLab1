# Open Questions for the Instructors

The handout says plainly:

> As you read through this document, you may experience some uncertainty about the meaning or
> interpretation of certain requirements. **You must clarify all such uncertainties before
> finalizing your design.**

Clarifying these is a graded expectation, not optional diligence. Ask at the TA progress update,
and record the answer here with the date.

| # | Question | Why it matters | Our current assumption | Answer |
|---|---|---|---|---|
| Q1 | **Dates.** The Lab 01 slides say Lab 1 is due "Sunday, September 23", the progress update is the week of Sept 9 and checkoff the week of Sept 16. September 23 2026 is a **Wednesday**, so the deck appears to be recycled from a previous year. | The whole schedule depends on it. | Due end of the week of Sept 21; checkoff week of Sept 16. | |
| Q2 | **Req 4d vs Req 4.** Requirement 4 says a sensor whose button is off should display "Sensor n off". Requirement 4d says the display must notify the user if *any* sensor is unplugged or faulty. What should the box show for a sensor that is both **off** and **faulty**? | Changes the display logic and the checkoff demonstration. | We show "Sensor n off ERR" -- both facts in one 16-character row, satisfying both readings. | |
| Q3 | **Req 3, "data not available from the internet."** Is a hard power switch that kills the whole box acceptable, or must the box stay powered and actively refuse to serve data? | A hard switch is simpler and more obviously correct; a soft switch would need the radio to stay up. | Hard mechanical break in the battery line, using our SPDT wired as on/off. | |
| Q4 | **Req 5, "appropriate software running on the computer."** Is a local service plus a browser UI acceptable as the computer software, or is a native desktop application expected? | Determines whether our FastAPI + browser architecture is acceptable at all. | A local service with a browser front end counts. | |
| Q5 | **Req 7, "text/email."** Is an email delivered to a carrier SMS gateway (so it arrives as a text) acceptable, or is a real SMS service such as Twilio required? | Twilio costs money and needs an account; the gateway is free. | Carrier gateway is acceptable. | |
| Q6 | **Req 1c, "battery operated."** Must the box run from battery during the demo, or is it enough that it *can*? | Affects how we present the checkoff. | We will demo on battery. | |
| Q7 | **Req 5c.i, fixed 10–50 °C limits.** Requirement 8 wants a design range of −10 to +63 °C, but the graph is pinned to 10–50 °C. Confirm the graph really should clip rather than autoscale. | We have built it to clip and mark off-scale points. Autoscaling would be a bug. | Fixed limits always, off-scale clearly marked. | |
| Q8 | **Network.** Is there a lab network we may use, or should we bring our own hotspot? Campus eduroam is WPA2-Enterprise and often has client isolation. | Determines connection code and demo logistics. | We bring our own hotspot or travel router. | |
| Q9 | **Report template.** The slides mention a lab report template will be provided. Where is it posted? | Structures the deliverable. | Not yet received. | |
| Q10 | **Req 8c in a warm lab.** The requirement expects about 22 C at room temperature, +/- 4, so 18-26 C. Our bench reads 26.7 C (80 F), just over the top of that band. If the room genuinely sits above 26 C, a correct thermometer fails the stated test. How should we demonstrate 8c? | Determines whether this is a sensor problem or a room problem. | Pending the ice-bath result: if T-8d passes, the probes are accurate and the room is warm. | |

## How to use this file

1. Bring it to the TA progress update (week of Sept 9, pending Q1).
2. Fill in the **Answer** column with the answer and the date.
3. If an answer changes the design, update
   [the traceability matrix](00-requirements-traceability.md) in the same commit.
