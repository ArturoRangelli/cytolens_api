"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

OpenAI utilities for generating clinical summaries
"""

from openai import OpenAI

from utils import constants

client = OpenAI(api_key=constants.OPENAI_API_KEY)


def generate_clinical_summary(data):
    """
    Generate a clinical summary based on region and cell data from multiple images of a single slide.
    """
    # Define system and user messages for the OpenAI Chat API
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant specializing in thyroid cytology. "
                "Your task is to evaluate the provided data and generate a clinical summary. "
                "Analyze the adequacy of the sample, summarize the distribution of Bethesda categories, "
                "and highlight any notable findings. The provided data consists of multiple images from a single slide."
                "Ensure that when referring to specific images, you use their **file names** rather than their numerical file IDs."
            ),
        },
        {
            "role": "user",
            "content": (
                f"""
                Analyze the following thyroid cytology data from multiple images of a single slide and provide a clinical summary.
                When referring to specific images, **always use the file_name instead of file_id.**

                1. **Sample Adequacy**:
                   - A slide is considered satisfactory if the following condition is met:
                     - Across all images, there must be at least **six groups**, each containing at least **10 cells**.
                   - If this condition is not met, mention that the sample may require additional consultation.

                2. **Bethesda Category Distribution**:
                   - Provide an **overview of Bethesda categories** detected across all images.
                   - Summarize the **distribution as percentages** and indicate which category is dominant.
                   - If multiple Bethesda categories are present within a single group, highlight this.
                   - Identify any groups that contain an **unusual mix of Bethesda categories.**
                   - Always refer to the **file_name** when discussing specific images.

                3. **Notable Findings (Outliers)**:
                   - If any group contains **cells categorized differently** from the dominant category in that group, highlight them.
                   - List the **specific cell names** and their Bethesda categories for easy reference.
                   - When mentioning where an outlier cell was found, always refer to the **file_name**, not the file ID.

                **Data for analysis (JSON format)**:
                {data}

                Please generate a concise but detailed clinical summary based on the above criteria, ensuring that all references to images use their respective file names.
                """
            ),
        },
    ]

    # Call the OpenAI Chat API using the client
    completion = client.chat.completions.create(
        model="gpt-4",  # Adjust to "gpt-4o" or other models if needed
        messages=messages,
        temperature=0.7,  # Control response randomness
    )

    # Access the message content directly
    return completion.choices[0].message.content
