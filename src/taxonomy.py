"""Classification taxonomy for technology fields and subfields."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldDefinition:
    """Definition of a classification field."""

    name: str
    description: str
    subfields: list[str]
    keywords: list[str]


# Main taxonomy of technology fields
TAXONOMY: dict[str, FieldDefinition] = {
    "Robotics": FieldDefinition(
        name="Robotics",
        description="Robotic systems, automation, and autonomous machines",
        subfields=[
            "Industrial Robotics",
            "Medical Robotics",
            "Autonomous Vehicles",
            "Drones & UAVs",
            "Human-Robot Interaction",
            "Robotic Manipulation",
            "Mobile Robots",
            "Soft Robotics",
        ],
        keywords=["robot", "automation", "autonomous", "manipulator", "drone", "UAV"],
    ),
    "MedTech": FieldDefinition(
        name="MedTech",
        description="Medical devices, diagnostics, therapeutics, and healthcare technology",
        subfields=[
            "Medical Devices",
            "Diagnostics",
            "Therapeutics",
            "Drug Delivery",
            "Medical Imaging",
            "Surgical Tools",
            "Wearable Health",
            "Telemedicine",
            "Small Molecule Drugs",
            "Biologics",
            "Cell Therapy",
            "Gene Therapy",
        ],
        keywords=[
            "medical", "health", "therapeutic", "diagnostic", "drug", "pharmaceutical",
            "clinical", "patient", "disease", "treatment", "surgery", "imaging",
        ],
    ),
    "Biotechnology": FieldDefinition(
        name="Biotechnology",
        description="Biological systems, genetic engineering, and life sciences",
        subfields=[
            "Synthetic Biology",
            "Genetic Engineering",
            "Protein Engineering",
            "Bioprocessing",
            "Bioinformatics",
            "Genomics",
            "Proteomics",
            "Microbiome",
            "Fermentation",
        ],
        keywords=[
            "biology", "genetic", "DNA", "RNA", "protein", "cell", "organism",
            "enzyme", "microbe", "fermentation", "bioreactor",
        ],
    ),
    "Agriculture": FieldDefinition(
        name="Agriculture",
        description="Agricultural technology, food science, and farming systems",
        subfields=[
            "Precision Agriculture",
            "AgTech Sensors",
            "Crop Science",
            "Animal Health",
            "Food Processing",
            "Aquaculture",
            "Vertical Farming",
            "Soil Science",
            "Irrigation Systems",
        ],
        keywords=[
            "agriculture", "farm", "crop", "plant", "soil", "irrigation",
            "livestock", "food", "harvest", "seed", "fertilizer",
        ],
    ),
    "Energy": FieldDefinition(
        name="Energy",
        description="Energy generation, storage, and efficiency technologies",
        subfields=[
            "Solar Energy",
            "Wind Energy",
            "Battery Technology",
            "Fuel Cells",
            "Energy Storage",
            "Grid Technology",
            "Nuclear Energy",
            "Hydrogen",
            "Carbon Capture",
            "Energy Efficiency",
        ],
        keywords=[
            "energy", "power", "battery", "solar", "wind", "fuel", "electricity",
            "renewable", "grid", "storage", "carbon", "emission",
        ],
    ),
    "Computing": FieldDefinition(
        name="Computing",
        description="Computer science, software, AI, and information technology",
        subfields=[
            "Artificial Intelligence",
            "Machine Learning",
            "Computer Vision",
            "Natural Language Processing",
            "Cybersecurity",
            "Cloud Computing",
            "Quantum Computing",
            "Data Analytics",
            "Software Engineering",
            "Distributed Systems",
        ],
        keywords=[
            "computer", "software", "algorithm", "AI", "machine learning", "data",
            "neural", "network", "security", "cloud", "quantum", "computing",
        ],
    ),
    "Materials": FieldDefinition(
        name="Materials",
        description="Advanced materials, nanomaterials, and materials science",
        subfields=[
            "Nanomaterials",
            "Polymers",
            "Composites",
            "Ceramics",
            "Metals & Alloys",
            "Coatings",
            "Smart Materials",
            "Biomaterials",
            "Semiconductors",
        ],
        keywords=[
            "material", "nano", "polymer", "composite", "ceramic", "metal",
            "coating", "surface", "alloy", "semiconductor",
        ],
    ),
    "Electronics": FieldDefinition(
        name="Electronics",
        description="Electronic devices, circuits, and semiconductor technology",
        subfields=[
            "Integrated Circuits",
            "Sensors",
            "Displays",
            "Photonics",
            "Wireless Communication",
            "Signal Processing",
            "Power Electronics",
            "MEMS",
            "Printed Electronics",
        ],
        keywords=[
            "electronic", "circuit", "sensor", "display", "wireless", "signal",
            "photonic", "optical", "LED", "transistor", "chip",
        ],
    ),
    "Environmental": FieldDefinition(
        name="Environmental",
        description="Environmental technology, sustainability, and pollution control",
        subfields=[
            "Water Treatment",
            "Air Quality",
            "Waste Management",
            "Recycling",
            "Remediation",
            "Environmental Monitoring",
            "Sustainable Materials",
        ],
        keywords=[
            "environment", "pollution", "water", "air", "waste", "recycle",
            "sustainable", "green", "clean", "remediation",
        ],
    ),
    "Aerospace": FieldDefinition(
        name="Aerospace",
        description="Aviation, space technology, and aerospace systems",
        subfields=[
            "Propulsion",
            "Aerodynamics",
            "Satellite Technology",
            "Space Systems",
            "Aviation Safety",
            "Aircraft Design",
        ],
        keywords=[
            "aerospace", "aircraft", "satellite", "space", "propulsion", "flight",
            "aviation", "rocket", "orbit",
        ],
    ),
    "Manufacturing": FieldDefinition(
        name="Manufacturing",
        description="Manufacturing processes, 3D printing, and industrial technology",
        subfields=[
            "Additive Manufacturing",
            "3D Printing",
            "Process Optimization",
            "Quality Control",
            "Supply Chain",
            "Industrial IoT",
        ],
        keywords=[
            "manufacturing", "3D print", "additive", "production", "factory",
            "industrial", "process", "assembly",
        ],
    ),
    "Other": FieldDefinition(
        name="Other",
        description="Technologies that don't fit other categories",
        subfields=[
            "Consumer Products",
            "Education Technology",
            "Entertainment",
            "Construction",
            "Transportation",
            "Other",
        ],
        keywords=[],
    ),
}


def get_top_fields() -> list[str]:
    """Get list of all top-level fields."""
    return list(TAXONOMY.keys())


def get_subfields(top_field: str) -> list[str]:
    """Get subfields for a given top field."""
    if top_field in TAXONOMY:
        return TAXONOMY[top_field].subfields
    return []


def get_all_subfields() -> list[tuple[str, str]]:
    """Get all (top_field, subfield) pairs."""
    pairs = []
    for top_field, definition in TAXONOMY.items():
        for subfield in definition.subfields:
            pairs.append((top_field, subfield))
    return pairs


def get_field_description(top_field: str) -> Optional[str]:
    """Get description for a top field."""
    if top_field in TAXONOMY:
        return TAXONOMY[top_field].description
    return None


def format_taxonomy_for_prompt() -> str:
    """Format the taxonomy as a string for inclusion in LLM prompts."""
    lines = ["Available classification fields and subfields:\n"]

    for top_field, definition in TAXONOMY.items():
        lines.append(f"\n{top_field}: {definition.description}")
        lines.append("  Subfields:")
        for subfield in definition.subfields:
            lines.append(f"    - {subfield}")

    return "\n".join(lines)
