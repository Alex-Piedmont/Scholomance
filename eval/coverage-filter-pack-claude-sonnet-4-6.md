# Coverage Filter — Frozen Pack Eval
**Model:** Claude Sonnet 4.6  
**Date scored:** 2026-08-31

---

## KEEP / DROP Table

| id | Decision | Headline (KEEP) or reason (DROP) | Capability | Source outlet + date | Why |
|----|----------|----------------------------------|------------|----------------------|-----|
| 1 | **KEEP** | UGA Researchers Develop New System for Spray Drones | Automated station that measures, mixes, and loads agricultural chemicals directly onto spray drones — 10× faster than manual prep | RFD-TV / Farm Monitor, 24 Aug 2026 | Named farm-trade journalist (Neal Burnette-Irwin, Farm Monitor) outside the university; original agricultural-media reporting, not a campus PR reprint |
| 2 | **KEEP** | Southampton AI uncovers hidden clues in breast cancer | AI platform (CenSegNet) that maps centrosome abnormalities across whole tumour samples at single-cell resolution to stratify breast-cancer risk | BBC News, 24 Aug 2026 | BBC staff correspondent Naj Modak, South of England; original broadcast-journalism article with independent sourcing |
| 3 | **KEEP** | Nanoparticles ease Alzheimer's by making neurons from other cells | Nanoparticle cage (TN-PTBP1) that crosses the blood-brain barrier and deploys antibodies to convert astrocytes into replacement neurons in an Alzheimer's mouse model | New Scientist, Aug 2026 | Original specialist journalism with independent expert commentary (Lakatos/Cambridge, Berninger/KCL) and critical framing beyond the lab pitch |
| 4 | **KEEP** | Earthquake sensors reveal vital information about how hurricanes move and grow | Seismoacoustic sensor network repurposed to continuously measure hurricane boundary-layer turbulence, track eyewall structure, and calibrate intensity models | Physics World, 24 Aug 2026 | Named reporter Preetish Kakoty (UCL / ABSW Media Fellow); original specialist-journalism article citing publication in *Science*; includes interview with researcher Dunham |
| 5 | **KEEP** | Researchers harness sunlight to generate quantum entanglement | Solar concentrator + nonlinear crystal system that replaces laser pumps with focused sunlight to generate entangled photon pairs at lab-comparable rates | Physics World, 25 Aug 2026 | Named IOP Publishing writer Lauren Matthews; original specialist-journalism piece covering collaborative Ottawa + MPI research published in *Optica* |
| 6 | **KEEP** | Georgia Tech Develops Robot Guide Dog *(11Alive local TV)* | Quadruped robotic guide dog designed to navigate and assist blind/visually-impaired users at a fraction of the cost and lifespan limitations of trained animals | 11Alive (Atlanta NBC affiliate), 24 Sep 2025 | Independent local TV station; URL and segment title confirm original on-air coverage of GT technology; note: URL returned Access Denied during scoring — outlet is clearly independent TV |
| 7 | DROP | — | — | research.gatech.edu (GT research newsroom) | University research newsroom — explicitly excluded source |
| 8 | **KEEP** | Giant Robotic Bugs Are Headed to Farms | Many-legged centipede robot that traverses rough farm terrain without onboard sensors, enabling autonomous weeding in fields inaccessible to wheeled or conventional robots | IEEE Spectrum, 16 May 2025 | Original specialist journalism by Evan Ackerman, IEEE Spectrum's named robotics editor; independent coverage of Ground Control Robotics spinout of Goldman/GT SCUTTLE research |
| 9 | DROP | — | — | news.research.gatech.edu (GT research newsroom) | University research newsroom — explicitly excluded source |
| 10 | DROP | — | — | 3D Printing Industry, Nov 2025 | Trade reprint of the Authentise company press release; same quotes verbatim; no named reporter, no independent reporting |
| 11 | DROP | — | — | Authentise company press release | Company-only press release — explicitly excluded source |
| 12 | DROP | — | — | news.research.gatech.edu (GT research newsroom) | University research newsroom — also returned 404 Not Found |
| 13 | DROP | — | — | news.gatech.edu (GT university news) | University newsroom — explicitly excluded source |
| 14 | DROP | — | — | phys.org | phys.org wire reprint — explicitly excluded source |
| 15 | DROP | — | — | physics.gatech.edu (GT School of Physics news) | University/college-site news — explicitly excluded source |
| 16 | DROP | — | — | licensing.research.gatech.edu (GT TTO) | TTO/licensing page — explicitly excluded; also returned 404 Not Found |
| 17 | DROP | — | — | news.research.gatech.edu (GT research newsroom) | University research newsroom — explicitly excluded source |
| 18 | DROP | — | — | create-x.gatech.edu (CREATE-X page) | CREATE-X / Q-i program page — explicitly excluded source |
| 19 | **KEEP** | Georgia Tech students complete first simulated Mars mission | First entirely student-run analog astronaut mission in the US: 10-day isolation in an Arkansas missile silo with simulated Mars comms delays, EVAs, and onboard research | GPB (Georgia Public Broadcasting), 19 Aug 2026 | Named reporter Amanda Andrews (GPB News); independent public broadcaster; original reporting with on-the-record student interviews |
| 20 | **KEEP** | Why Georgia Tech students are living in a missile silo | Same student-led analog Mars mission — six-member crew in an isolated former nuclear missile silo, with all hardware and mission control architecture engineered by students | FOX 5 Atlanta, Aug 2026 | FOX 5 reporter Rob DiRienzo visited Mission Control on campus; independent local TV news with on-site reporting and named interviews |

---

## KEEP IDs

1, 2, 3, 4, 5, 6, 8, 19, 20

---

## Full KEEP Writeups

---

### 1 — UGA Drone Dock (RFDTV / Farm Monitor)

**Headline:** UGA Researchers Develop New System for Spray Drones

**Summary:** A team at the University of Georgia's Precision Horticulture Lab in Tifton, led by researcher Luan Oliveira, has developed the Drone Dock — an automated ground station that measures, mixes, and delivers crop-protection chemicals directly to a spray drone. Preliminary testing found the system is ten times faster than manual chemical preparation and loading. Researchers note the technology can improve precision application, including spot-spraying, and enables drone operations after heavy rainfall when ground machinery cannot access fields. The system targets productivity bottlenecks that currently slow commercial adoption of agricultural spray drones.

**Capability:** Automated docking station that prepares and loads agricultural spray chemicals onto drones 10× faster than manual methods, enabling faster field coverage and targeted applications.

**Sources:** RFD-TV / Farm Monitor, Neal Burnette-Irwin, 24 Aug 2026 — https://www.rfdtv.com/uga-researchers-develop-new-system-for-spray-drones

**Why independent:** Named farm-trade journalist (Farm Monitor / RFD-TV) outside the university covered the research; original agricultural-media reporting, not a campus press-release reprint or phys.org clone.

---

### 2 — Southampton CenSegNet (BBC News)

**Headline:** Southampton AI uncovers hidden clues in breast cancer

**Summary:** Researchers at the University of Southampton, working with Southampton's hospital, have built CenSegNet, an AI platform that maps centrosome abnormalities across entire tumour samples at single-cell resolution. The team analysed more than 330,000 cells from 127 patients, discovering two distinct types of centrosome defect — numerical excess and abnormal enlargement — that had previously been treated as a single category. Tumours with higher numbers of enlarged centrosomes were more likely to show features of aggressive disease, including lymph-node spread. Patients with fewer enlarged centrosomes in the tumour core tended to have better survival. CenSegNet is released as free open-source software and has been validated on kidney, colon, and appendix tissue as well.

**Capability:** AI tool that classifies two distinct categories of centrosome abnormality at single-cell scale across whole tumour sections to stratify cancer risk and identify potential drug targets.

**Sources:** BBC News (Naj Modak, South of England), 24 Aug 2026 — https://www.bbc.co.uk/news/articles/cq56x317pq0o

**Why independent:** BBC staff correspondent filed an original report with named researcher quotes; this is broadcast/national newspaper journalism independent of the university's communications office.

---

### 3 — USC Nano-ERASER / TN-PTBP1 nanogel (New Scientist)

**Headline:** Nanoparticles ease Alzheimer's by making neurons from other cells

**Summary:** Peisheng Xu's lab at the University of South Carolina has developed TN-PTBP1, a drug that packages antibodies targeting the PTBP1 protein inside nanoparticle cages. The cages cross the blood-brain barrier and release the antibodies inside astrocytes, causing those support cells to convert into replacement neurons. In mice engineered to develop Alzheimer's, two intravenous doses over two weeks restored nest-building and maze-navigation to near-normal levels and new neuron growth was confirmed in hippocampal samples. Independent experts at Cambridge and King's College London provided cautionary but broadly positive commentary. The team plans fluorescent-labelling studies in mice and then primate and human trials.

**Capability:** Intravenous nanoparticle drug that reprograms brain support cells (astrocytes) into replacement neurons, reversing neurodegeneration in an Alzheimer's mouse model without permanent genetic editing.

**Sources:** New Scientist, Aug 2026 — https://www.newscientist.com/article/2586426-nanoparticles-ease-alzheimers-by-making-neurons-from-other-cells/

**Why independent:** Original specialist journalism with independent expert quotes (András Lakatos/Cambridge, Benedikt Berninger/KCL) who were not involved in the research; New Scientist commissioned the piece editorially, not via a campus PR wire.

---

### 4 — Stanford Seismoacoustic Hurricane Sensing (Physics World)

**Headline:** Earthquake sensors reveal vital information about how hurricanes move and grow

**Summary:** Qing Ji, Ipshita Dey, and Eric Dunham at Stanford University processed data from seismoacoustic stations in Louisiana — part of a 1,700-station US network — to study Hurricane Isaac's landfall in 2012. The infrasound sensors in those stations, designed to measure seismic pressure, also captured the hurricane's turbulent boundary-layer pressure fluctuations. The team could resolve the calm eye, the turbulent eyewall, and the outer rain bands from station data alone. A key finding corrected existing modelling assumptions: the relevant parameter for calculating Earth's elastic response to pressure fluctuations is the *downstream advection velocity* of those fluctuations, not the near-surface wind speed. The researchers argue the existing seismoacoustic network could be expanded for continuous hurricane monitoring without new dedicated hardware.

**Capability:** Method for repurposing existing earthquake sensor networks to continuously track hurricane structure, boundary-layer turbulence, and intensity without reconnaissance aircraft or dedicated atmospheric sensors.

**Sources:** Physics World (Preetish Kakoty), 24 Aug 2026 — https://physicsworld.com/a/earthquake-sensors-reveal-vital-information-about-how-hurricanes-move-and-grow/

**Why independent:** Named reporter who is an independent science journalist (UCL postdoc / ABSW Media Fellow); includes direct interview with researcher Dunham; cites publication in *Science*; IOP Publishing editorial, not a campus PR placement.

---

### 5 — Ottawa / MPI Sunlight-Pumped Entangled Photons (Physics World)

**Headline:** Researchers harness sunlight to generate quantum entanglement

**Summary:** A collaboration between Robert Boyd's group at the University of Ottawa (theory) and Hanieh Fattahi's group at the Max Planck Institute for the Science of Light (hardware) has demonstrated that focused sunlight can replace lasers as the pump source for spontaneous parametric down-conversion (SPDC), producing pairs of entangled photons. The team built a solar concentrator using a Fresnel lens, spectral filter, and glass-cone light guide to focus sunlight onto a fibre thinner than a human hair, then directed it into a nonlinear crystal. The generated photons violated Bell's inequality with an S value of 2.54 (threshold: 2) and achieved 94% fidelity to the target Bell state. When normalised for spectral bandwidth, the photon-pair generation rate is comparable to laser-pumped systems. The approach eliminates the laser energy cost and opens a path to space-based quantum systems on sun-synchronous orbits.

**Capability:** Solar concentrator system that produces quantum-entangled photon pairs using sunlight instead of lasers, enabling energy-efficient quantum computing and communication links without electrical-to-optical conversion.

**Sources:** Physics World (Lauren Matthews), 25 Aug 2026 — https://physicsworld.com/a/researchers-harness-sunlight-to-generate-quantum-entanglement/

**Why independent:** IOP Publishing editorial piece with researcher quotes and technical context; named writer; covers collaborative multi-institution research published in *Optica*; not a campus press release.

---

### 6 — Walker / Ha Robotic Guide Dog (11Alive)

**Headline:** Georgia Tech Develops Robot Guide Dog *(11Alive local TV)*

**Summary:** *(Note: URL returned Access Denied during scoring. Assessment is based on outlet identity and URL path, which confirm an independently produced 11Alive news segment on the GT robot guide dog — consistent with the subject matter covered in item 7.)* Georgia Tech researchers Bruce Walker and Sehoon Ha are developing a quadruped robotic guide dog intended as an accessible alternative to trained service animals, which can cost up to $50,000 and have fewer than ten working years. The robot is designed to navigate environments autonomously, communicate hazards to its owner verbally, and include an SOS function. 11Alive (Atlanta's NBC affiliate) covered the project as an independently reported local TV news segment.

**Capability:** Quadruped robotic guide dog with autonomous navigation, obstacle detection, and owner-communication features designed to assist blind and visually impaired users at lower lifetime cost than biological guide dogs.

**Sources:** 11Alive (Atlanta NBC affiliate), 24 Sep 2025 — https://www.11alive.com/video/news/local/11alive-news-the-take-georgia-tech-develops-robot-guide-dog-92425/85-01b1c13e-d3b7-4c5a-aae9-52f42e16e0ad

**Why independent:** 11Alive is a commercial local broadcast-television station (NBC affiliate) with no institutional affiliation with Georgia Tech; local TV qualifies as independent TV coverage under scout rules. URL returned Access Denied during scoring — content could not be verified from the page text itself.

---

### 8 — Goldman SCUTTLE / Ground Control Robotics (IEEE Spectrum)

**Headline:** Giant Robotic Bugs Are Headed to Farms

**Summary:** *(Article text partially loaded due to paywall truncation; scored on available content and outlet/author credentials.)* IEEE Spectrum's robotics editor Evan Ackerman covered Ground Control Robotics — the commercialisation spinout from Daniel Goldman's Georgia Tech lab — and its many-legged centipede-style robots targeting farm weeding applications. The underlying SCUTTLE research, published in *Science* (2023), showed that adding redundant leg pairs lets robots traverse uneven terrain without active sensing. Ground Control Robotics is applying this to crop fields where weedkillers are ineffective and standard wheeled robots cannot operate reliably.

**Capability:** Many-legged centipede robot that uses leg redundancy instead of active sensors to traverse rough agricultural terrain reliably, enabling precision weeding on uneven crop fields.

**Sources:** IEEE Spectrum (Evan Ackerman, robotics editor), 16 May 2025 — https://spectrum.ieee.org/ground-control-robot-insects

**Why independent:** Original specialist journalism by a named IEEE Spectrum staff editor; IEEE Spectrum is the benchmark specialist-trade outlet named in scout rules; coverage is editorially independent of the university and the spinout company.

---

### 19 — GT Analog Mars Habitat — GPB (Georgia Public Broadcasting)

**Headline:** Georgia Tech students complete first simulated Mars mission

**Summary:** Southeast Analog, a student-run programme at Georgia Tech, completed SEA-1 Thalassa — described as one of the first entirely student-led analog astronaut missions in the United States. Six crew members spent ten days in a decommissioned nuclear missile silo in Arkansas eating freeze-dried food, breathing recycled air, and performing extravehicular activities including soil sampling and rover tele-operation, while 30 mission-control crew on campus operated around the clock with a simulated 20-minute one-way communication delay. All hardware — suits, the command-centre communication system, and onboard research gear — was designed and built by students in approximately ten months. GPB reporter Amanda Andrews covered the mission's completion with interviews from the flight director and head of research.

**Capability:** Student-engineered analog astronaut programme that tests human factors, operations, and research protocols for long-duration Mars missions using isolated Earth-based habitats with realistic comms delays.

**Sources:** GPB News (Amanda Andrews, reporter), 19 Aug 2026 — https://www.gpb.org/news/2026/08/19/georgia-tech-students-complete-first-simulated-mars-mission

**Why independent:** Georgia Public Broadcasting is an independent public broadcaster (NPR/PBS affiliate); named reporter filed an original story with multiple student interviews; not a university press-release reprint.

---

### 20 — GT Analog Mars Habitat — FOX 5 Atlanta

**Headline:** Why Georgia Tech students are living in a missile silo

**Summary:** FOX 5 Atlanta reporter Rob DiRienzo visited Georgia Tech's Mission Control on campus and interviewed Southeast Analog founder Vic Paulson and incoming president Gabriel Buggi. The report covers the same SEA-1 Thalassa mission: a six-member crew isolated 500+ miles away in an Arkansas missile silo for ten days, with all hardware and operational protocols engineered by students across more than 30 universities. DiRienzo reported on the 20-minute signal-delay simulation, the students' six months of pre-mission training, and Paulson's ambition to support crewed Mars missions in her lifetime.

**Capability:** Student-engineered analog astronaut programme (same as item 19) covering mission design, suit hardware, command-centre architecture, and human-factors research for Mars-duration isolation.

**Sources:** FOX 5 Atlanta (Rob DiRienzo), Aug 2026 — https://www.fox5atlanta.com/news/why-georgia-tech-students-living-missile-silo

**Why independent:** FOX 5 Atlanta is a commercial local TV station (Fox affiliate); reporter visited Mission Control in person; original on-site reporting with named on-camera interviews; fully independent of the university's communications office.
