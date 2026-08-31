# Coverage filter pack — grok-4.6

Frozen-URL scoring only. Each item judged as coverage of the named technology from the given URL(s). No extra sourcing. No patent/DB matching. No user stories, diamonds, demand, or proceed/hold/archive recs.

**KEEP ids:** 1, 2, 3, 4, 5, 6, 8, 19, 20

## Table

| id | KEEP or DROP | headline or (drop) | capability or — | source outlet+date | why |
|----|--------------|--------------------|-----------------|--------------------|-----|
| 1 | KEEP | UGA researchers develop new system for spray drones | Dock that measures, mixes, and loads chemicals onto a farm spray drone | RFD-TV / Farm Monitor, 24 Aug 2026 | Original farm-TV reporting with a named RFD News producer, not campus PR |
| 2 | KEEP | Southampton AI uncovers hidden clues in breast cancer | AI that reads breast-tumor cells one by one to flag hidden division defects tied to worse disease | BBC News (Naj Modak), 24 Aug 2026 | BBC regional original reporting with researcher interview |
| 3 | KEEP | Nanoparticles ease Alzheimer's by making neurons from other cells | Nanoparticle package that turns brain support cells into new neurons in Alzheimer's-model mice | New Scientist, 2026 (Cell Biomaterials paper; day not shown on fetched page) | Named specialist magazine; staff rewrite plus independent outside-expert quotes |
| 4 | KEEP | Earthquake sensors reveal vital information about how hurricanes move and grow | Existing quake/infrasound stations used to track a hurricane's eye, winds, and turbulence at landfall | Physics World (Preetish Kakoty), 24 Aug 2026 | IOP specialist journalism with original interviews, not a campus reprint |
| 5 | KEEP | Researchers harness sunlight to generate quantum entanglement | Sunlight concentrator that makes entangled photon pairs without a laser | Physics World (Lauren Matthews), 25 Aug 2026 | IOP specialist journalism on the Ottawa/MPI experiment, not a university newsroom |
| 6 | KEEP | Georgia Tech develops robot guide dog | Robot dog meant to guide visually impaired people as an alternative to a living service animal | 11Alive News: The Take, 24 Sep 2025 | Atlanta TV news package with on-air professor interview |
| 7 | DROP | (university newsroom) | — | Georgia Tech Research News Center, 10 Sep 2025 | Campus research.gatech.edu newsroom |
| 8 | KEEP | Giant robotic bugs are headed to farms | Many-legged robots that crawl under crops to scout and pull weeds on rough ground | IEEE Spectrum (Evan Ackerman), 16 May 2025 (print Aug 2025) | Staff robotics editor feature with original Goldman interview |
| 9 | DROP | (university newsroom) | — | GT Research News Center, 5 May 2023 | Campus news.research.gatech.edu newsroom |
| 10 | DROP | (trade reprint of partner PR) | — | 3D Printing Industry (Rodolfo Hernandez), 27 Nov 2025 | Trade rewrite of the Authentise/Kform/OpenWerks launch PR (same CEO quotes and feature list) |
| 11 | DROP | (company PR) | — | Authentise press release, 20 Nov 2025 | Company-only press release |
| 12 | DROP | (university newsroom) | — | GT Research News Center URL, 17 Feb 2026 | Campus news.research.gatech.edu (page 404 at scoring; still TTO/newsroom class) |
| 13 | DROP | (university newsroom) | — | news.gatech.edu (Chloe Morris), 18 Feb 2026 | Georgia Tech News Center campus copy |
| 14 | DROP | (phys.org / wire reprint) | — | phys.org, 21 Jun 2023 (byline: Rebecca Jacobson, NIST) | phys.org reprint of NIST copy, not independent journalism |
| 15 | DROP | (college/lab news) | — | GT School of Physics news, 23 Apr 2019 | University college/lab site |
| 16 | DROP | (TTO listing) | — | GT Office of Technology Licensing URL | TTO/licensing page (404 at scoring; still TTO class) |
| 17 | DROP | (university newsroom / Q-i) | — | GT Research News Center, 26 Feb 2026 | Campus newsroom on Quadrant-i / CreationsVC fellows, not independent coverage of SatSLAM |
| 18 | DROP | (CREATE-X page) | — | create-x.gatech.edu/node/10899 | CREATE-X portfolio page for OpenWerks |
| 19 | KEEP | Georgia Tech students complete first simulated Mars mission | Student-run analog Mars habitat: isolated crew plus Atlanta mission control with a Mars-like delay | GPB News (Amanda Andrews), 19 Aug 2026 | Georgia Public Broadcasting original radio/web report with reporter-shot photos and interviews |
| 20 | KEEP | Why Georgia Tech students are living in a missile silo | Same analog: crew in an Arkansas missile-silo habitat, 24/7 Atlanta control with a 20-minute delay | FOX 5 Atlanta (Rob DiRienzo), 17 Aug 2026 | Local TV reporter visited mission control and interviewed student leads |

## KEEP writeups

### 1 — UGA Drone Dock (Luan Oliveira, Precision Horticulture Lab, Tifton)

**Headline:** UGA researchers develop new system for spray drones

**Summary:** A University of Georgia team in Tifton is building a “Drone Dock” that measures, mixes, and delivers spray chemicals straight into an agricultural drone. Farm-TV reporting says early tests made that prep step about ten times faster than doing it by hand. Researchers argue spray drones matter when rain keeps ground rigs out of fields, and when a grower only needs to hit spots rather than a whole acreage. The piece is a short RFD-TV / Farm Monitor story aimed at farmers, not a lab announcement.

**Capability:** A dock that mixes and loads chemicals onto a spray drone so farmers do not have to do it by hand.

**Sources:** RFD-TV (Neal Burnette-Irwin / Farm Monitor), 24 August 2026, https://www.rfdtv.com/uga-researchers-develop-new-system-for-spray-drones

**Why independent:** National farm television with a named RFD News digital producer; original reporting, not a UGA newsroom or TTO page.

### 2 — Southampton CenSegNet (Salah Elias)

**Headline:** Southampton AI uncovers hidden clues in breast cancer

**Summary:** BBC News reports that University of Southampton researchers, working with the city’s hospital, used an AI tool on more than 330,000 cells from 127 breast-cancer patients. The software, CenSegNet, found two kinds of centrosome defects that doctors had been treating as one, and linked extra-large centrosomes to more aggressive disease. Patients with fewer of those enlarged structures in the tumor core tended to live longer. The tool is open-source and not yet in routine hospital use, but the team says it also works on kidney, colon, and appendix tissue. Dr Salah Elias is interviewed on camera/page about what the patterns could mean for picking high-risk patients.

**Capability:** Software that scans tumor samples cell by cell to spot hidden cell-division defects linked to more dangerous breast cancers.

**Sources:** BBC News (Naj Modak, South of England), 24 August 2026, https://www.bbc.co.uk/news/articles/cq56x317pq0o

**Why independent:** BBC original regional reporting with a named correspondent and researcher interview, not a university press release.

### 3 — USC Nano-ERASER / PTBP1 nanogel (Peisheng Xu)

**Headline:** Nanoparticles ease Alzheimer's by making neurons from other cells

**Summary:** New Scientist describes a University of South Carolina approach that packages antibodies inside nanoparticles so they can cross into the brain and temporarily knock down PTBP1, a protein that keeps star-shaped support cells from becoming neurons. In dishes of human cells, the drug (TN-PTBP1) turned those support cells into nerve cells. In mice with an Alzheimer’s-like illness, two intravenous doses restored nesting and maze performance to roughly healthy-mouse levels, and new neurons appeared in the hippocampus. Outside experts at Cambridge and King’s College London are quoted on both the promise and the need to check that the new cells do not scramble brain networks. Human tests are years away.

**Capability:** A nanoparticle drug that converts brain support cells into new neurons, tested in mice with Alzheimer’s-like disease.

**Sources:** New Scientist, 2026, https://www.newscientist.com/article/2586426-nanoparticles-ease-alzheimers-by-making-neurons-from-other-cells/

**Why independent:** Named specialist magazine article with original explanation and independent outside-scientist quotes, not a USC newsroom or TTO page.

### 4 — Stanford seismoacoustic hurricane sensing (Qing Ji, Ipshita Dey, Eric Dunham)

**Headline:** Earthquake sensors reveal vital information about how hurricanes move and grow

**Summary:** Physics World reports that Stanford researchers mined Louisiana earthquake stations—built to listen to the ground, not the sky—during Hurricane Isaac in 2012. The stations’ infrasound and seismometer traces picked up the calm eye, the violent eyewall, and the rainbands as the storm moved over land. That matters because the turbulent layer right above the surface is hard to measure once a hurricane comes ashore: planes are dangerous, and towers are sparse. The team used the records to model how pressure fluctuations ride with the storm, and found the key speed is how those fluctuations travel downstream, not the near-surface wind speed people had assumed. Dunham and Ji are interviewed about using existing seismoacoustic networks for weather.

**Capability:** Reads existing earthquake and infrasound sensors to track how a hurricane’s eye, winds, and turbulence change at landfall.

**Sources:** Physics World (Preetish Kakoty), 24 August 2026, https://physicsworld.com/a/earthquake-sensors-reveal-vital-information-about-how-hurricanes-move-and-grow/

**Why independent:** IOP Publishing specialist journalism by a named writer, with original researcher interviews, not a Stanford newsroom reprint.

### 5 — Ottawa / MPI sunlight-pumped entangled photons (Boyd / Fattahi)

**Headline:** Researchers harness sunlight to generate quantum entanglement

**Summary:** Physics World covers a University of Ottawa / Max Planck Institute for the Science of Light experiment that uses concentrated sunlight, not a lab laser, to create pairs of entangled photons. A Fresnel lens, filter, and glass cone squeeze sunlight down to a couple of millimeters, couple it into a fiber, and send it into a crystal that splits photons into entangled pairs. The team had to track the Sun, fight stray light, and even start measurements before dawn. The sunlight-fed pairs violated Bell’s inequality (S = 2.54) with about 94% fidelity to the target state, and, per spectral bandwidth, made pairs at a rate comparable to laser pumping. Fattahi discusses field-deployable and space uses where electricity for lasers is scarce.

**Capability:** A sunlight collector that produces entangled photon pairs without a powered laser.

**Sources:** Physics World (Lauren Matthews), 25 August 2026, https://physicsworld.com/a/researchers-harness-sunlight-to-generate-quantum-entanglement/

**Why independent:** IOP specialist article on the Ottawa/MPI work, written for Physics World, not a university or institute press office.

### 6 — Walker/Ha robotic guide dog

**Headline:** Georgia Tech develops robot guide dog

**Summary:** 11Alive’s local news video (“The Take,” 24 September 2025) reports that Georgia Tech has developed a robot guide dog for visually impaired people who need an alternative to a living service animal. Professor Bruce Walker of Interactive Computing appears to explain the project on air. The given URL is an Atlanta NBC-affiliate news package, not a pasted campus release. (The video page itself is a TV player; this KEEP is for that broadcast, not for any accompanying university copy.)

**Capability:** A robot dog that can guide a visually impaired person when a trained service dog is not an option.

**Sources:** 11Alive News: The Take, 24 September 2025, https://www.11alive.com/video/news/local/11alive-news-the-take-georgia-tech-develops-robot-guide-dog-92425/85-01b1c13e-d3b7-4c5a-aae9-52f42e16e0ad

**Why independent:** Local television news with a named professor interview, not a Georgia Tech newsroom, lab, or TTO page.

### 8 — Goldman SCUTTLE / Ground Control Robotics

**Headline:** Giant robotic bugs are headed to farms

**Summary:** IEEE Spectrum’s robotics editor writes a feature on Georgia Tech physicist Dan Goldman’s Atlanta startup Ground Control Robotics. The robots are long, segmented, many-legged machines that “swim” through clutter by adding legs rather than adding sensors and compute. Goldman is interviewed on why that helps under blueberries, strawberries, and steep vineyards, where big wheeled machines would damage plants and small robots usually get stuck. The company is piloting with a Georgia blueberry grower and a vineyard; the near-term job is scouting, then later ripping weeds. Spectrum ran it as a May 2025 web story and an August 2025 print feature (“A Helpful Bug for Farmers”).

**Capability:** Cheap many-legged robots that crawl under crops to inspect plants and pull weeds on rough, cluttered ground.

**Sources:** IEEE Spectrum (Evan Ackerman), 16 May 2025 (print August 2025), https://spectrum.ieee.org/ground-control-robot-insects

**Why independent:** Named IEEE Spectrum staff feature with original Goldman interview and editor analysis; not a GT newsroom, spinout site, or partner PR reprint.

### 19 — GT analog Mars habitat

**Headline:** Georgia Tech students complete first simulated Mars mission

**Summary:** GPB News reports that Georgia Tech’s student group Southeast Analog finished its first 10-day simulated Mars mission. Six “astronauts” lived in isolation at an Arkansas habitat while about 30 students ran mission control in Atlanta, including a roughly 20-minute one-way comms delay. Reporter Amanda Andrews photographed mission control and interviewed flight director Alan Yeung and research lead Sara Kapasi about freeze-dried food, night EVAs, and daily exercise. The piece treats the analog as a student-run spaceflight training/research exercise, and notes an Atlanta City Council proclamation.

**Capability:** A student-run analog Mars mission: isolated crew plus Atlanta control with a Mars-like communications delay.

**Sources:** GPB News (Amanda Andrews), 19 August 2026, https://www.gpb.org/news/2026/08/19/georgia-tech-students-complete-first-simulated-mars-mission

**Why independent:** Georgia Public Broadcasting original radio/web report with reporter-credited photos and interviews, not campus PR.

### 20 — Same analog (FOX 5)

**Headline:** Why Georgia Tech students are living in a missile silo

**Summary:** FOX 5 Atlanta’s Rob DiRienzo visited SEA-1 Thalassa mission control on Georgia Tech’s campus while six crew members lived in a former nuclear missile silo (Titan Ranch, Vilonia, Arkansas). Founder Vic Paulson and incoming president Gabriel Buggi describe building suits, voice-loop comms, and onboard research in about ten months, plus the 20-minute delay and 24/7 shifts. The 10-day isolation (freeze-dried food, recycled air, daily exercise) started 7 August 2026. The station presents it as original local TV, not a university handout.

**Capability:** Same analog Mars habitat: isolated silo crew and Atlanta mission control operating with a 20-minute delay.

**Sources:** FOX 5 Atlanta (Rob DiRienzo), 17 August 2026, https://www.fox5atlanta.com/news/why-georgia-tech-students-living-missile-silo

**Why independent:** Local TV reporter on campus with original interviews; not a Georgia Tech newsroom or CREATE-X/Q-i page.
