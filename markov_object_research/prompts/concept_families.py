"""
Curated prompt families for Markov object detection.

Each family represents a concept that should activate a stable bounded region
in the model if Markov objects exist. Prompts within a family vary surface form
while preserving conceptual content — the hypothesis is they cluster together.
"""

CONCEPT_FAMILIES = {
    "arithmetic_addition": [
        "1 + 1 = 2",
        "Two plus two equals four",
        "The sum of three and five is eight",
        "Adding seven to nine gives sixteen",
        "What is four plus four?",
        "If you add six to six you get twelve",
    ],
    "love_romantic": [
        "I love you",
        "She loves him deeply",
        "Love is a powerful emotion",
        "He fell in love with her",
        "Their love was unconditional",
        "Love is blind",
    ],
    "spatial_above": [
        "The bird flew above the clouds",
        "The lamp hangs over the table",
        "Stars are high above us",
        "The plane is flying overhead",
        "She held the umbrella above her head",
        "The ceiling is above the floor",
    ],
    "negation": [
        "There is no water in the glass",
        "She did not arrive on time",
        "Nothing was left on the shelf",
        "He never answered the question",
        "The door is not open",
        "None of the lights were on",
    ],
    "causation": [
        "The fire caused the smoke",
        "Rain made the ground wet",
        "He broke the window because he threw a ball",
        "The drug reduced the fever",
        "Heat causes ice to melt",
        "The crash resulted from brake failure",
    ],
    "past_tense": [
        "She walked to the store yesterday",
        "They finished the project last week",
        "He ran the race in the morning",
        "The meeting ended an hour ago",
        "We arrived before sunset",
        "The train departed at noon",
    ],
}
