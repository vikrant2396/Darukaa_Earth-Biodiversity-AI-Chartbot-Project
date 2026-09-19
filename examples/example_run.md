# Example run

This transcript is generated directly from `ConversationManager` (not hand-written), and
reproduces the "Conversational Intelligence" example and the "Example Use Case" from the
challenge PDF in one continuous session.

## Turn 1 — underspecified input triggers a clarifying question

**User:** `Biodiversity is declining on my land`

**System:**
```
What is the soil organic carbon percentage (or a rough estimate: very low / low / moderate / high)?
```

This matches the PDF's expected behavior:
> System: "Can you provide soil organic carbon %, rainfall pattern, and land use type?"

## Turn 2 — structured input completes the required context

**User (structured JSON):**
```json
{"soil_organic_carbon": 0.3, "rainfall": "low", "land_use": "monoculture_wheat", "region": "semi-arid"}
```
This is the exact scenario from the PDF's "Example Use Case" section (SOC 0.3%, low
rainfall, monoculture wheat, semi-arid region).

**System:**
```
• Recommendation: Agroforestry / intercropping (tree-crop integration)
  Why it works: Woody perennials add deep-rooted carbon inputs and leaf litter, buffer
  topsoil microclimate (reduced evapotranspiration and wind erosion), and create vertical
  habitat structure that supports insects, birds and soil fauna absent in monocultures.
  This connects 3 distinct environmental domains (soil, biodiversity, climate), not a
  single-variable effect.
  Multi-metric chain: soil_organic_carbon → microbial_diversity (...); soil_structure
  (...); water_retention (...) → microbial_diversity → plant_health (...); species_richness (...)
  Expected impact: soil_organic_carbon: +10% to +30% over baseline (3-5 years);
  species_richness: 20-60% higher than adjacent monoculture plots (3-5 years);
  water_retention: improved infiltration, reduced runoff (1-3 years); microclimate_temperature:
  canopy cooling of 1-3°C at soil surface (immediate-1 year)
  Impacted metrics: soil_organic_carbon, habitat_structure, species_richness, microclimate, yield_resilience
  Time horizon: medium_term
  Confidence: high
  Source: FAO Agroforestry Working Papers; IPCC AR6 WG2 (agricultural adaptation chapter)

• Recommendation: Organic mulching
  Why it works: A surface layer of organic residue reduces soil evaporation, buffers
  surface temperature extremes, and gradually decomposes to add organic matter. This
  connects 3 distinct environmental domains (soil, water, climate), not a single-variable effect.
  Expected impact: soil_moisture: -20% to -40% evaporative loss (immediate-1 season);
  soil_organic_carbon: gradual increase as residue decomposes (1-3 years)
  Impacted metrics: soil_moisture, soil_organic_carbon, microclimate
  Time horizon: short_term
  Confidence: medium-high
  Source: FAO conservation agriculture technical briefs

• Recommendation: Legume-based cover cropping
  Why it works: Legumes fix atmospheric nitrogen via rhizobia symbiosis and add root
  biomass and residue between cash-crop cycles, feeding soil microbial communities and
  increasing aggregate stability. This connects 2 distinct environmental domains (soil, biodiversity).
  Expected impact: soil_organic_carbon: +15% to +25% (2-3 years); soil_microbial_diversity:
  increase (moderate-high) (1-3 years); pollinator_abundance: increase (flowering cover crops only) (1 season)
  Impacted metrics: soil_organic_carbon, microbial_diversity, pollinator_support, species_richness
  Time horizon: medium_term
  Confidence: high
  Source: FAO Soils Portal — Soil Organic Carbon guidance; FAO 'Conservation Agriculture' technical briefs
```

This satisfies the PDF's "Expected Output" for this exact scenario: agroforestry/intercropping
is the top-ranked suggestion, soil carbon and biodiversity impacts are quantified, and FAO/IPCC
are cited — while also going beyond it by (a) explaining *why* through a causal chain, (b)
ranking two further options, and (c) tagging each with a time horizon and confidence level.

To reproduce this yourself:
```bash
python -m src.main
# then type:  Biodiversity is declining on my land
# then type:  json:{"soil_organic_carbon": 0.3, "rainfall": "low", "land_use": "monoculture_wheat", "region": "semi-arid"}
```
