import os
import streamlit as st
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient

# ✅ Write google-ads.yaml from secrets
def write_google_ads_yaml():
    credentials = st.secrets["google_ads"]
    yaml_content = f"""
developer_token: "{credentials['developer_token']}"
client_id: "{credentials['client_id']}"
client_secret: "{credentials['client_secret']}"
refresh_token: "{credentials['refresh_token']}"
use_proto_plus: {str(credentials['use_proto_plus']).lower()}
login_customer_id: "{credentials['login_customer_id']}"
    """.strip()

    with open("google-ads.yaml", "w") as f:
        f.write(yaml_content)

# Run setup
write_google_ads_yaml()

st.set_page_config(page_title="Keyword Research Agent", layout="wide")
st.title("🔍 Keyword Research Agent for RSOC / AFS Ads")

st.markdown("Enter a concept name or landing page URL below. This tool will return high-performing long-tail keywords with CPC, competition, and search volume.")

url_input = st.text_input("Enter URL or Concept Name")
seed_input = st.text_input("Optional: Add comma-separated seed keywords (e.g. 'eco office, green workspace')")
keyword_count = st.slider("How many keywords do you want?", min_value=50, max_value=1000, value=300, step=50)

# 🌍 Updated Country mapping
country_map = {
    "United States": "2840",
    "India": "2356",
    "Canada": "2124",
    "United Kingdom": "2826",
    "Australia": "2036",
    "Indonesia": "2052",
    "Bangladesh": "1236",
    "Pakistan": "1780",
    "Japan": "2392",
    "Vietnam": "2390",
    "Malaysia": "2060",
    "Thailand": "2394",
    "Mexico": "2126",
    "Philippines": "2402",
    "Egypt": "2081"
}

country = st.selectbox("Select Target Country", list(country_map.keys()))
location_id = country_map[country]

if url_input and st.button("Generate Keywords"):
    try:
        client = GoogleAdsClient.load_from_storage("google-ads.yaml")

        def get_keywords(client, customer_id, url, language_id="1000", location_id="2840", max_keywords=500, seed_keywords=None):
            keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
            request = client.get_type("GenerateKeywordIdeasRequest")

            request.customer_id = customer_id
            request.language = f"languageConstants/{language_id}"
            request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

            geo_target_constant = f"geoTargetConstants/{location_id}"
            request.geo_target_constants.append(geo_target_constant)

            request.url_seed.url = url

            if seed_keywords:
                request.keyword_seed.keywords.extend(seed_keywords)

            response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

            keywords = []
            for idea in response:
                keyword = idea.text
                if len(keyword.split()) < 3:
                    continue  # Only long-tail
                metrics = idea.keyword_idea_metrics
                keywords.append({
                    "Keyword": keyword,
                    "CPC (USD)": round(metrics.high_top_of_page_bid_micros / 1_000_000, 2),
                    "Competition": metrics.competition.name,
                    "Monthly Searches": metrics.avg_monthly_searches
                })

            return sorted(keywords, key=lambda x: x["Monthly Searches"], reverse=True)[:max_keywords]

        customer_id = st.secrets["google_ads"]["login_customer_id"]
        seeds = [s.strip() for s in seed_input.split(",")] if seed_input else []

        keywords = get_keywords(
            client,
            customer_id,
            url_input,
            location_id=location_id,
            max_keywords=keyword_count,
            seed_keywords=seeds
        )

        df = pd.DataFrame(keywords)
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="keywords.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Error: {e}")