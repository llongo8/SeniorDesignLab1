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
| Q5 | **Req 7, "text/email."** Two parts. (a) Must we deliver both a text *and* an email, or is one enough? (b) Is an email routed through a carrier SMS gateway an acceptable "text", or is a real SMS service such as Twilio required? | Decides how much of requirement 7 we have to build, and whether Twilio (paid, needs an account) is unavoidable. | (a) One is enough. Req 1d says a phone receiving "text messages **or** emails", and Req 7 says "text/email" to a "phone number/email address" -- every mention is disjunctive. (b) The gateway is acceptable. Either way our destination is a single address field, so we can demonstrate both. | |
| Q6 | **Req 1c, "battery operated."** Must the box run from battery during the demo, or is it enough that it *can*? | Affects how we present the checkoff. | We will demo on battery. | |
| Q7 | **Req 5c.i, fixed 10–50 °C limits.** Requirement 8 wants a design range of −10 to +63 °C, but the graph is pinned to 10–50 °C. Confirm the graph really should clip rather than autoscale. | We have built it to clip and mark off-scale points. Autoscaling would be a bug. | Fixed limits always, off-scale clearly marked. | |
| Q8 | **Network.** `UI-DeviceNet` is visible on campus alongside eduroam — presumably the device-registration network for hardware that cannot do enterprise auth. (a) May we register the ESP32 on it? (b) **Does it isolate clients from each other?** Our MAC is `20:50:0D:D9:62:A4`. | If it does not isolate clients, this solves the demo network with no phone and no personal credentials. If it does, it is useless to us and we stay on a hotspot. eduroam is out either way: WPA2-Enterprise needs a HawkID in plaintext in firmware, readable off the flash by anyone who picks the board up. | **RESOLVED 2026-09-09 — phone hotspot, no campus network.** The laptop cannot join UI-DeviceNet and must stay on eduroam, so the box and the PC would sit on different campus networks with no route between them. Both go on a phone hotspot instead: one network we control, no isolation question, identical behaviour in the lab and at home, and no personal credentials anywhere. Req 5 only asks for an internet-connected computer, which a laptop on a hotspot is. | Withdrawn |
| Q9 | **Report template.** The slides mention a lab report template will be provided. Where is it posted? | Structures the deliverable. | Not yet received. | |
| Q10 | **Req 8c in a warm lab.** The requirement expects about 22 C at room temperature, +/- 4, so 18-26 C. Our bench reads 26.7 C (80 F), just over the top of that band. If the room genuinely sits above 26 C, a correct thermometer fails the stated test. How should we demonstrate 8c? | Determines whether this is a sensor problem or a room problem. | **RESOLVED 2026-08-27 — no need to ask.** It was neither. The probes were lying on the breadboard beside the ESP32 and picking up its heat. In free air they read 21.7–22.2 °C, and the ice bath gives +0.6/−0.5 °C. Both requirements pass. | Withdrawn |

## How to use this file

1. Bring it to the TA progress update (week of Sept 9, pending Q1).
2. Fill in the **Answer** column with the answer and the date.
3. If an answer changes the design, update
   [the traceability matrix](00-requirements-traceability.md) in the same commit.
