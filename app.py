
import streamlit as st
from google.ads.googleads.client import GoogleAdsClient
import pandas as pd
import tempfile
import yaml

st.set_page_config(page_title="Keyword Research Agent", layout="wide")
st.title("🔍 Keyword Research Agent for RSOC / AFS Ads")

st.markdown("Enter a concept name or landing page URL below. This tool will return high-performing long-tail keywords with CPC, competition, and search volume.")

url_input = st.text_input("Enter URL or Concept Name")
seed_input = st.text_input("Optional: Add comma-separated seed keywords (e.g. 'eco office, green workspace')")
keyword_count = st.slider("How many keywords do you want?", min_value=50, max_value=1000, value=300, step=50)

# 🌍 Country mapping
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
    "Vietnam": "2390"
}

country = st.selectbox("Select Target Country", list(country_map.keys()))
location_id = country_map[country]

if url_input and st.button("Generate Keywords"):
    try:
        # 🔐 Load credentials from secrets.toml and write to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as temp_yaml:
            yaml.dump({
                "developer_token": st.secrets["google_ads"]["developer_token"],
                "client_id": st.secrets["google_ads"]["client_id"],
                "client_secret": st.secrets["google_ads"]["client_secret"],
                "refresh_token": st.secrets["google_ads"]["refresh_token"],
                "login_customer_id": st.secrets["google_ads"]["login_customer_id"],
                "use_proto_plus": True
            }, temp_yaml)
            temp_yaml_path = temp_yaml.name

        client = GoogleAdsClient.load_from_storage(temp_yaml_path)

        def get_keywords(client, customer_id, url, language_id="1000", location_id="2840", max_keywords=500, seed_keywords=None):
            keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
            request = client.get_type("GenerateKeywordIdeasRequest")

            request.customer_id = customer_id
            request.language = f"languageConstants/{language_id}"
            request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH

            # ✅ Properly formatted geo target constant
            geo_target_constant = f"geoTargetConstants/{location_id}"
            request.geo_target_constants.append(geo_target_constant)

            # ✅ Add URL as seed
            request.url_seed.url = url

            # ✅ Add seed keywords if provided
            if seed_keywords:
                request.keyword_seed.keywords.extend(seed_keywords)

            # 🔍 API Call
            response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

            # 📊 Parse response
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

        # 🧠 Prepare values
        customer_id = st.secrets["google_ads"]["login_customer_id"]
        seeds = [s.strip() for s in seed_input.split(",")] if seed_input else []

        # 🚀 Run
        keywords = get_keywords(
            client,
            customer_id,
            url_input,
            location_id=location_id,
            max_keywords=keyword_count,
            seed_keywords=seeds
        )

        # 📊 Show results
        df = pd.DataFrame(keywords)
        st.dataframe(df)

        # 📥 CSV Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", data=csv, file_name="keywords.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ Error: {e}")
