
import os
import xml.etree.ElementTree as ET
from pathlib import Path

project_path = Path(__file__).resolve().parents[1]

dataset_path = project_path / "data" / "raw" / "invoices"

# Find ground truth XML files
gt_files = list(dataset_path.rglob("*_gt.xml"))

print("=" * 60)
print("GROUND TRUTH XML CONTENT INSPECTION")
print("=" * 60)

print("\nTotal ground truth files:", len(gt_files))

if gt_files:

    sample_file = gt_files[0]

    print("\nSample file:", sample_file.name)

    tree = ET.parse(sample_file)
    root = tree.getroot()

    # Remove XML namespace from tag names
    def get_tag_name(tag):
        return tag.split("}")[-1]

    print("\nROOT:", get_tag_name(root.tag))

    print("\nTEXT CONTENT:")

    for element in root.iter():

        tag = get_tag_name(element.tag)

        if tag in ["TextRegion", "TextLine"]:
            print("\nElement:", tag, "ID:", element.get("id"))

            for child in element:
                child_tag = get_tag_name(child.tag)

                if child_tag == "Coords":
                    print("Coordinates:", child.get("points"))

                elif child_tag == "TextEquiv":
                    for subchild in child.iter():
                        if get_tag_name(subchild.tag) == "Unicode":
                            print("Actual text:", subchild.text)

    print("\nINSPECTION COMPLETED")

else:
    print("No ground truth XML files found!")
