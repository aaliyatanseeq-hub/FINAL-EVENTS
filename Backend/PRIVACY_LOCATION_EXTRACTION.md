# Privacy-Compliant Location Extraction

## Overview
This system uses a **practical, safer approach** for location extraction that complies with privacy best practices and Twitter's Terms of Service.

## Data Sources (Public Only)

### 1. Tweet Place Data (Primary Signal)
- **Source**: `tweet.geo.place_id` → `place.country_code` from Twitter API
- **Type**: Coarse country-level signal
- **Purpose**: Relevance scoring for event targeting
- **Privacy**: Public geo-tagging data, not individual tracking

### 2. User-Defined Location Field
- **Source**: `user.location` from Twitter API
- **Type**: User-provided text (may not be accurate)
- **Purpose**: Secondary signal for country inference
- **Privacy**: Public profile data

### 3. Content-Based Inference (Public Signals)
- **Keywords**: Country names, major cities (e.g., "New York", "London", "Tokyo")
- **Venues**: Major sports venues and stadiums (public knowledge)
- **Teams**: Local sports teams mentioned in tweets
- **Privacy**: Only uses publicly mentioned information

### 4. Timezone Inference (Coarse Signal)
- **Source**: Tweet posting time (UTC)
- **Method**: Approximate timezone inference from posting hour
- **Accuracy**: Very coarse (only used as last resort)
- **Privacy**: Public timestamp data, not precise location

## What We Store

✅ **Country-level data only** (e.g., "United States", "United Kingdom")
- No precise coordinates
- No IP addresses
- No street addresses
- No city-level precision (unless from user-defined field)

## What We Don't Store

❌ Precise coordinates
❌ IP addresses or IP-derived data
❌ Individual movement histories
❌ Precise timezone data
❌ Any data from "About this account" section (not available via API)

## Privacy & Terms of Service Compliance

### Our Approach:
1. **Only public data**: We use only publicly available Twitter data and optional tweet geo-tagging
2. **Coarse signals**: Country-level inference for personalization/analytics, not individual tracking
3. **No tracking**: We do not build per-user movement histories
4. **Transparency**: This document explains our data collection practices

### Twitter API Compliance:
- ✅ Uses official Twitter API v2
- ✅ Only requests public user fields
- ✅ Respects rate limits
- ✅ No web scraping
- ✅ No violation of Terms of Service

## Signal Priority

When multiple signals are available, we prioritize:

1. **Tweet Place Country** (most reliable)
2. **User Location Field** (user-defined, may be inaccurate)
3. **Content Inference** (keywords, venues, teams)
4. **Timezone Inference** (least reliable, only as fallback)

## Use Cases

- **Event Targeting**: Identify which country an event is relevant to
- **Analytics**: Aggregate country-level statistics
- **Personalization**: Show events relevant to user's country
- **NOT for**: Individual tracking, precise location services, or surveillance

## Data Retention

- Location data is stored with attendee records
- Used only for event relevance scoring
- No separate location tracking database
- Follows same retention policy as attendee data (3 months cache TTL)

## Updates

This approach may be updated as Twitter API evolves or privacy regulations change. All changes will maintain the principle of using only public, coarse, country-level signals.

