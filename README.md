# E-Commerce Omnichannel & Retention Analytics 📊

## 📖 Project Background
This project analyzes the digital storefront and omnichannel performance of a high-volume e-commerce retailer. With the platform serving as a critical research hub that influences over $100M in physical retail revenue, the primary objective of this analysis is to evaluate the end-to-end customer journey. The analysis focuses on identifying friction points in the conversion funnel, exposing the true ROI of acquisition channels, and uncovering strategic opportunities to maximize Customer Lifetime Value (LTV).

---

## 🎯 Executive Summary
This analysis evaluates the end-to-end customer journey of a high-volume e-commerce platform, focusing on acquisition efficiency, omnichannel behavior, and customer lifetime value (LTV). By integrating Funnel, Cohort, and RFM analyses, this project identifies critical revenue leaks and strategic growth opportunities.

**Key Findings:**
* **The Omnichannel Reality ($100M Offline Impact):** The website functions heavily as a research catalog for high-ticket items. While mobile drives 55% of online traffic with a low conversion rate (4.19%), online research directly influenced over $100M in in-store revenue, boasting a massive Average Order Value (AOV) of $1,628.
* **The 80/20 Retention Crisis:** The business relies heavily on a core 18% of the customer base (VIP & Loyal segments) to drive sustainable profitability. Conversely, 53% of customers are currently At-Risk or Lost, primarily driven by an 86% churn rate immediately following their first purchase (The Month 1 Cliff).
* **The Paid Acquisition Trap:** Paid Marketing Campaigns create a conversion illusion. They yield quick initial sales but fail to generate long-term value, bringing in the highest percentage of one-time buyers (Lost segment). In contrast, Organic Search and Direct traffic are the true LTV drivers, generating over 50% of all VIP customers.
* **The Checkout Bottleneck:** Despite a solid overall conversion rate (4.93%) indicating strong product-market fit, 66.4% of high-intent users abandon their carts at the final step, signaling severe UI/UX friction during the checkout process.

---

### 1. Funnel Performance: The Conversion Journey & Drop-off Analysis
Analyzing the user journey from the first click to the final purchase reveals that while the core product offerings are highly desired, technical friction is bottlenecking maximum revenue potential.
![image](<img width="1080" height="2400" alt="1000184087" src="https://github.com/user-attachments/assets/d378a261-4e70-4f09-9a2e-3201e3155e33" />)

* **Top-of-Funnel Leak: 47% of Traffic Bounces Before Viewing a Single Product**
  Although the platform attracts substantial traffic, nearly half of the visitors drop off before interacting with the product catalog (Visit-to-View rate is 52.65%). This early exit suggests a disconnect at the top of the funnel, potentially pointing to misaligned ad targeting bringing in low-intent traffic, or landing page performance issues (e.g., slow load times).
* **The Checkout Bottleneck: 66.4% of High-Intent Users Abandon Their Carts**
  The most critical friction point exists at the very end of the customer journey. Users demonstrate strong purchase intent by adding items to their carts, yet only 33.56% successfully complete the transaction. This massive 66.4% abandonment rate strongly indicates severe UI/UX flaws in the checkout process—such as hidden CTA buttons, forced account creation, or payment gateway friction.
* **The Silver Lining: A Solid 4.93% Overall Conversion Rate Validates Product-Market Fit**
  Despite the significant drop-offs at the very beginning and the very end of the funnel, the overall conversion rate stands at a highly competitive 4.93%. This is a strong positive indicator: the products are in demand, the pricing is competitive, and the catalog is appealing. The revenue loss is not a product or market issue; it is strictly a technical and user experience (UX) journey issue that can be optimized.

> *Data Quality & Tracking Note: A technical review of session timestamps reveals a near-identical average duration across all funnel stages (~4.4 mins). This strongly suggests an anomaly in event tracking or synthetic data generation constraints. However, the funnel drop-off volume (View -> Cart -> Purchase) remains logically sound and highly actionable for UX optimization.*

---

### 2. Omnichannel Behavior & Device Performance
By analyzing traffic sources and device usage against actual revenue, it becomes clear that the platform serves a dual purpose: a direct digital storefront and a highly effective interactive catalog for physical retail.

![ضع صورة الموبايل والديسكتوب هنـــــا]()

* **The Mobile Research Hub: Mobile Drives 55% of Traffic but Yields the Lowest Conversion (4.19%)**
  Despite dominating user acquisition with over 3.57 million visits (55% of total traffic), mobile platforms struggle to convert directly. In contrast, desktop traffic is significantly lower (1.62 million visits) but converts at a peak rate of 6.16%. Furthermore, desktop users view an average of 5.67 pages per session compared to just 3.77 on mobile, even though the average session duration is identical across both devices (2.85 minutes). This highlights severe mobile UI/UX friction that is wasting high-intent traffic.
* **The Webrooming Phenomenon: A $100M Offline Impact Driven by High AOV ($1,628)**
  The true value of mobile and overall website traffic extends far beyond online checkout. Online research directly influenced over $100 million in offline (in-store) revenue from just 61.7K customers. Breaking down this offline revenue reveals a massive Average Order Value (AOV) of approximately $1,628. This high price point perfectly explains the "Webrooming" behavior: customers hesitate to complete large transactions on their phones. Instead, they use mobile devices to research specifications and compare prices online, before ultimately visiting a physical store to inspect the product and purchase with absolute confidence.

---

### 3. Customer Base Health & Retention Dynamics (RFM & Cohort Analysis)
By integrating RFM segmentation with Cohort retention trends, we can look beyond top-of-funnel acquisition to evaluate the true health of the customer base. This analysis uncovers a stark contrast between a highly profitable core audience and a massive, immediate retention leak.

![ضع صورة الكوهورت والـ RFM هنـــــا]()

* **The Retention Crisis: 53% of the Database is Churning, While a Core 18% Sustains the Business**
  Following the Pareto (80/20) principle, this business relies heavily on a small core of users—VIPs (7%) and Loyal Customers (11%)—who make up only 18% of the total base but drive continuous, high-margin revenue with near-zero re-acquisition costs. Conversely, a staggering 53% of the database is either 'Lost' (25%) or 'At Risk' (28%), highlighting a massive profitability leak.
* **The Month-1 Cliff: An 86% Immediate Churn Rate Exposes Onboarding Flaws**
  Cohort analysis pinpoints exactly when the 'Lost' segment bleeds out. Across acquisition cohorts, an alarming 80-86% of customers churn immediately after their first purchase. For example, the January cohort dropped from 1,840 initial buyers to just 258 users in Month 1. The platform is highly effective at driving the first transaction but fails to create immediate post-purchase stickiness.
* **The Retention Engine: A 70% Repeat Purchase Rate Drives a "Smile" Retention Curve**
  Despite the severe Month-1 drop-off, the overall repeat purchase rate stands at a robust 70%. Interestingly, cohort retention rates unconventionally increase over time (e.g., the January cohort rebounded from 14% to 25.7% by Month 11). This "Smile Curve" indicates a 3-to-4 month buying cycle, aligning perfectly with the high-ticket nature of the products ($1,628 AOV). Once the initial churn is mitigated, the Long-Term Value (LTV) model is highly profitable.
* **The Q4 Resurrection: End-of-Year Seasonality Reactivates Dormant Users**
  A visual inspection of the cohort matrix reveals a sudden spike in retention across all previous cohorts during the final months of the year (reaching peaks of 25–27%). End-of-year and holiday campaigns successfully wake up dormant users, proving that early-churned customers are not permanently lost, but rather require targeted, seasonal re-engagement.

---

### 4. Marketing ROI: The Acquisition Trap vs. Organic Loyalty
Evaluating traffic sources purely by top-of-funnel conversion rates creates a highly deceptive narrative. By cross-referencing clickstream acquisition channels with our RFM customer segments, the true Long-Term Value (LTV) and ROI of each marketing channel are definitively exposed.

![ضع صورة مصادر الترافيك والـ RFM هنـــــا]()

* **The Paid Acquisition Trap: High Initial Conversion, Zero Loyalty**
  At first glance, Marketing Campaigns appear highly effective, driving the highest add-to-cart rates (35.12%) and overall funnel conversion (7.10%). However, RFM data exposes the "Conversion Illusion": these campaigns predominantly attract "discount hunters." Campaign traffic forms the highest percentage of the 'Lost' (9.1%) and 'Regular' (10.7%) segments, but the absolute lowest in the 'VIP' segment (only 3.0%). The Customer Acquisition Cost (CAC) spent here is essentially wasted on one-time buyers who contribute heavily to the Month-1 churn.
* **The Hidden Treasure: Organic & Direct Traffic Drive Over 50% of VIPs**
  Conversely, un-paid channels look terrible initially. Direct and Referral traffic have the lowest top-of-funnel conversion rates (~3.5%) and a massive 55%+ bounce rate (users leaving without viewing a single product). However, the small percentage of users who do buy from these channels are the true "whales." Organic Search accounts for 27.8% of all VIPs, and Direct traffic accounts for 22.9%. Brand-aware customers who specifically seek out the platform yield the highest LTV, regardless of initial funnel friction.
* **The At-Risk Goldmine: 'At-Risk' Customers Share the Exact DNA as VIPs**
  The most actionable finding in the entire analysis lies within the 'At Risk' segment. Their traffic source distribution (27.8% Organic, 22.0% Direct) is a near-perfect mirror image of the highly profitable 'VIP' segment. This definitively proves that 'At Risk' users are not low-quality leads acquired through cheap ads; they are potential VIPs who slipped through the cracks due to a lack of post-purchase engagement. Reactivating this specific group is a guaranteed high-ROI objective.

---

### 5. Actionable Recommendations & Strategic Roadmap
To translate these analytical findings into measurable revenue growth, the following strategic initiatives should be prioritized across their respective departments:

**For the Product & UX Team:**
* **Eliminate Checkout Friction:** With 66.4% of high-intent users abandoning their carts, a complete UX audit of the checkout flow is mandatory. Implementing one-click express checkout options (e.g., Apple Pay, Google Pay) is crucial, especially to rescue mobile users who represent 55% of all traffic but suffer from the lowest conversion rate (4.19%).
* **Bridge the Digital-Physical Gap:** Capitalize on the $100M offline revenue and "webrooming" behavior by adding a prominent "Check In-Store Availability" feature directly on high-ticket product pages to facilitate offline conversion.
* **Conduct Mobile UX A/B Testing & Optimize Core Web Vitals:** Address the high bounce rate at the top of the funnel by running rigorous A/B tests on the mobile interface. Focus on enlarging CTA button sizes, minimizing form fields, and improving page load speeds (Core Web Vitals). Resolving this poor mobile experience is the most critical step to stopping the hemorrhage of top-of-funnel traffic.

**For the Operations & Retail Team:**
* **Implement BOPIS (Buy Online, Pick Up In-Store):** Since users hesitate to purchase $1,600+ items entirely online without physical inspection, offering BOPIS will secure the transaction digitally while satisfying the customer's need for physical validation.
* **Unify Omnichannel Loyalty:** Develop a unified Loyalty Program where customers earn and redeem points seamlessly across both the website and physical branches. This ensures accurate LTV tracking across channels and highly incentivizes the core 18% of users (VIPs & Loyal).

**For the Growth & Marketing Team:**
* **Reallocate CAC to 'At-Risk' Retargeting:** Immediately halt budget increases for generic, discount-driven campaigns, which currently fuel the 86% Month-1 churn rate and populate the 'Lost' segment. Instead, reallocate this ad spend toward retargeting the 'At-Risk' segment. Since their acquisition DNA (Organic/Direct) perfectly mirrors the VIP segment, they are highly recoverable.
* **Deploy a Month-1 Retention Sequence:** Combat the massive 86% initial drop-off (The Month 1 Cliff) by launching an automated post-purchase "Welcome Series." This should focus on product education, warranty details, and brand value to build trust before the next 3-to-4 month buying cycle begins.
* **Launch a VIP Referral Program:** Capitalize on the robust 70% repeat purchase rate by turning satisfied customers into brand advocates. Implementing a "Give $20, Get $20" referral program will organically scale Direct and Organic traffic—which our RFM analysis proved to be the absolute best sources for acquiring VIPs.
* **Capitalize on Q4 Seasonality with Targeted Re-engagement:** Allocate 20% of the October and November marketing budget specifically to re-engage dormant customers (those whose last purchase was 6 to 9 months ago). Utilize exclusive seasonal offers, such as VIP Black Friday early access, to directly leverage the previously identified Q4 cohort resurrection trend.

---

### 6. Next Steps & Success Metrics (Tracking Dashboard)
To ensure these strategic initiatives drive the desired business impact, a dedicated tracking dashboard must be established to continuously monitor three vital KPIs post-implementation:

1. **Cart Abandonment Rate:** To measure the success of the checkout UI/UX updates and express payment integrations.
2. **Month-1 Retention Rate:** To validate the effectiveness of the new automated "Welcome Series" onboarding sequence.
3. **'At-Risk' Activation Rate:** To track the conversion efficiency of the reallocated retargeting budget on the 'At-Risk' segment.
