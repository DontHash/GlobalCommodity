"""Complete, plain-language labels for HS chapter categories."""

from __future__ import annotations

import re


CATEGORY_LABEL_OVERRIDES = {
    "01": "Live animals",
    "02": "Meat and edible animal organs",
    "03": "Fish and seafood",
    "04": "Dairy products, eggs and honey",
    "05": "Other animal products",
    "06": "Live plants, bulbs, roots and cut flowers",
    "07": "Edible vegetables, roots and tubers",
    "08": "Fruit, nuts and citrus or melon peel",
    "09": "Coffee, tea, mate and spices",
    "10": "Cereals",
    "11": "Milled grains, malt, starches, inulin and wheat gluten",
    "12": "Oil seeds, grains, medicinal plants and fodder",
    "13": "Lac, gums, resins and plant extracts",
    "14": "Plant materials for weaving and plaiting",
    "15": "Animal and vegetable fats and oils",
    "16": "Prepared meat and seafood",
    "17": "Sugar and confectionery",
    "18": "Cocoa and cocoa products",
    "19": "Cereal, flour, starch and milk products",
    "20": "Prepared vegetables, fruit and nuts",
    "21": "Other prepared foods",
    "22": "Beverages, spirits and vinegar",
    "23": "Food industry residues and animal feed",
    "24": "Tobacco products and substitutes",
    "25": "Salt, sulphur, earth, stone, plaster, lime and cement",
    "26": "Ores, slag and ash",
    "27": "Mineral fuels and oils",
    "28": "Inorganic chemicals and metal compounds",
    "29": "Organic chemicals",
    "30": "Pharmaceutical products",
    "31": "Fertilizers",
    "32": "Dyes, pigments, paints, inks and tanning extracts",
    "33": "Essential oils, perfumes, cosmetics and toiletries",
    "34": "Soap, lubricants, waxes and candles",
    "35": "Proteins, modified starches, glues and enzymes",
    "36": "Explosives, fireworks and matches",
    "37": "Photography and film products",
    "38": "Other chemical products",
    "39": "Plastics and plastic products",
    "40": "Rubber and rubber products",
    "41": "Raw hides, skins and leather",
    "42": "Leather goods, saddlery and travel goods",
    "43": "Fur and artificial fur products",
    "44": "Wood, wood products and charcoal",
    "45": "Cork and cork products",
    "46": "Basketware and woven plant products",
    "47": "Wood pulp, cellulose materials and recovered paper",
    "48": "Paper, paperboard and paper products",
    "49": "Books, newspapers and printed materials",
    "50": "Silk",
    "51": "Wool and animal-hair textiles",
    "52": "Cotton",
    "53": "Plant textile fibres, paper yarn and woven fabrics",
    "54": "Man-made filament fibres",
    "55": "Man-made staple fibres",
    "56": "Wadding, felt, nonwoven fabrics, twine and rope",
    "57": "Carpets and textile floor coverings",
    "58": "Woven fabrics, lace, tapestry and embroidery",
    "59": "Coated and laminated textiles",
    "60": "Knitted and crocheted fabrics",
    "61": "Knitted clothing and accessories",
    "62": "Non-knitted clothing and accessories",
    "63": "Textile products, sets and used clothing",
    "64": "Footwear, gaiters and parts",
    "65": "Headwear and parts",
    "66": "Umbrellas, walking sticks, seat-sticks and whips",
    "67": "Feathers, artificial flowers and human-hair products",
    "68": "Stone, plaster, cement, asbestos and mica products",
    "69": "Ceramic products",
    "70": "Glass and glassware",
    "71": "Pearls, gemstones, precious metals and coins",
    "72": "Iron and steel",
    "73": "Iron and steel products",
    "74": "Copper and copper products",
    "75": "Nickel and nickel products",
    "76": "Aluminium and aluminium products",
    "78": "Lead and lead products",
    "79": "Zinc and zinc products",
    "80": "Tin and tin products",
    "81": "Other base metals and cermets",
    "82": "Metal tools and cutlery",
    "83": "Other base-metal products",
    "84": "Machinery and mechanical equipment",
    "85": "Electrical machinery and equipment",
    "86": "Railway vehicles and equipment",
    "87": "Road vehicles and parts",
    "88": "Aircraft, spacecraft and parts",
    "89": "Ships, boats and floating structures",
    "90": "Optical, photographic, measuring and medical instruments",
    "91": "Clocks, watches and parts",
    "92": "Musical instruments and parts",
    "93": "Weapons, ammunition and parts",
    "94": "Furniture, lighting, signs and prefabricated buildings",
    "95": "Toys, games and sports equipment",
    "96": "Other manufactured products",
    "97": "Art, collectibles and antiques",
    "99": "Unspecified commodities",
}


def category_label(raw: str) -> str:
    """Return the canonical label for a raw HS category value."""
    value = str(raw)
    if value == "all_commodities":
        return "All commodities"
    code = value.partition("_")[0]
    if code in CATEGORY_LABEL_OVERRIDES:
        return CATEGORY_LABEL_OVERRIDES[code]

    text = re.sub(r"^\d+_", "", value).replace("_", " ").strip()
    text = re.sub(r"\bthereof\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnes\b", "other", text, flags=re.IGNORECASE)
    text = re.sub(r"\betc\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return text.capitalize() or value
