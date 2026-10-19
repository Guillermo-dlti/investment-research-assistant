# Stage 5 results: questions answered from selected filing chunks

Model `Qwen/Qwen2.5-3B-Instruct` (greedy decoding), approximate retrieval, top 10 candidates, at most 4 chunks and 1100 words of context, chunks with Jaccard >= 0.5 against a kept chunk dropped as redundant.
Times are milliseconds on an Apple M4 Pro. Retrieval time covers search only; selection and generation are listed separately.

## Summary

| # | Question | Filters | Retrieval ms | Candidates | Selected | Cited | Generation ms |
|---|---|---|---|---|---|---|---|
| 1 | What was NVIDIA data center revenue in fiscal 2025? | ticker=NVDA, fiscal_year=2025 | 4.48 | 223 | 4 | [1] | 2966 |
| 2 | How much did NVIDIA spend on research and development in fiscal 2024? | ticker=NVDA, fiscal_year=2024 | 4.81 | 190 | 4 | [1] | 2906 |
| 3 | Who does NVIDIA consider its main competitors? | ticker=NVDA | 2.24 | 248 | 4 | [2] | 2121 |
| 4 | nvidea gaming revenue | none | 5.79 | 762 | 4 | [2] | 2898 |
| 5 | What risks does AMD describe about export restrictions to China? | ticker=AMD | 2.72 | 242 | 4 | [1], [2], [3] | 3649 |
| 6 | How does AMD describe its data center segment? | ticker=AMD | 1.99 | 236 | 4 | [1], [3] | 4624 |
| 7 | What does AMD say about the acquisition of ZT Systems? | ticker=AMD | 3.76 | 401 | 4 | [2], [4] | 2936 |
| 8 | How much did Microsoft Azure and other cloud services revenue grow in fiscal 2025? | ticker=MSFT, fiscal_year=2025 | 3.46 | 223 | 4 | [1] | 2521 |
| 9 | What does Microsoft say about its investments in artificial intelligence? | ticker=MSFT | 3.64 | 406 | 4 | [2] | 2214 |
| 10 | microsft cloud revenue | none | 5.61 | 820 | 4 | [3], [4] | 3474 |
| 11 | What does Apple say about iPhone net sales in fiscal 2025? | ticker=AAPL, fiscal_year=2025 | 2.80 | 144 | 4 | [1] | 3336 |
| 12 | How does Apple describe its services revenue? | ticker=AAPL | 2.20 | 226 | 4 | [2], [3] | 4977 |
| 13 | How many employees does Apple have? | ticker=AAPL | 1.43 | 199 | 4 | [1] | 1869 |
| 14 | What risks does Apple describe about manufacturing in China? | ticker=AAPL | 1.78 | 226 | 4 | [1] | 1736 |
| 15 | What are Alphabet's main sources of revenue? | ticker=GOOGL | 1.04 | 84 | 4 | [1], [4] | 3947 |
| 16 | What does Google say about YouTube advertising revenue? | ticker=GOOGL | 3.55 | 359 | 4 | [2] | 1974 |
| 17 | What legal or antitrust matters does Alphabet describe? | ticker=GOOGL | 2.25 | 340 | 4 | [1], [2] | 5024 |
| 18 | Which companies depend on TSMC to manufacture their chips? | none | 2.43 | 399 | 4 | [1] | 2132 |
| 19 | What is Tesla revenue from electric vehicles? | none | 2.78 | 536 | 4 | none | 1789 |
| 20 | What is the outlook? | none | 0.13 | 11 | 4 | [1] | 4287 |
| 21 | How did share repurchases change in fiscal 2025? | fiscal_year=2025 | 4.63 | 721 | 4 | [2] | 3192 |

## 1. What was NVIDIA data center revenue in fiscal 2025?

- Filters: ticker `NVDA`, fiscal year `2025`
- Retrieval: 4.48 ms, 223 candidate chunks; selection 0.087 ms, 972 words selected
- Selection decisions: NVDA_2025_10K_0255 selected, NVDA_2025_10K_0144 selected, NVDA_2025_10K_0256 selected, NVDA_2025_10K_0154 selected, NVDA_2025_10K_0149 limit, NVDA_2025_10K_0165 limit, NVDA_2025_10K_0155 limit, NVDA_2025_10K_0251 limit, NVDA_2025_10K_0257 limit, NVDA_2025_10K_0062 limit

**Selected context**

1. `NVDA_2025_10K_0255`, NVIDIA Corporation FY2025, score 0.937: "United States for fiscal years 2025 and 2024 was primarily due to higher U.S.-based Compute & Networking segment demand. We refer to customers who purchase products directly from NVIDIA as direct customers, such as AIBs, distributors, ODMs, OEMs, and system integrators. We have certain customers that may purchase products directly from NVIDIA and may use either internal resources or third-party ..."
2. `NVDA_2025_10K_0144`, NVIDIA Corporation FY2025, score 0.932: "6. [Reserved] 35 Table of Contents Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations The following discussion and analysis of our financial condition and results of operations should be read in conjunction with “Item 1A. Risk Factors,” our Consolidated Financial Statements and related Notes thereto, as well as other cautionary statements and risks described elsewhere ..."
3. `NVDA_2025_10K_0256`, NVIDIA Corporation FY2025, score 0.917: "11,317 Networking | 12,990 | 8,575 | 3,688 Gaming | 11,350 | 10,447 | 9,067 Professional Visualization | 1,878 | 1,553 | 1,544 Automotive | 1,694 | 1,091 | 903 OEM and Other | 389 | 306 | 455 Total revenue | $ | 130,497 | $ | 60,922 | $ | 26,974 The following table presents summarized information for ..."
4. `NVDA_2025_10K_0154`, NVIDIA Corporation FY2025, score 0.900: "expenses | $ | 16,405 | $ | 11,329 | Up 45% Operating income | $ | 81,453 | $ | 32,972 | Up 147% Net income | $ | 72,880 | $ | 29,760 | Up 145% Net income per diluted share | $ | 2.94 | $ | 1.19 | Up 147% We specialize in markets where our ..."

**Answer** (2966 ms)

> [1] NVIDIA data center revenue in fiscal 2025 was $115,186 million.

## 2. How much did NVIDIA spend on research and development in fiscal 2024?

- Filters: ticker `NVDA`, fiscal year `2024`
- Retrieval: 4.81 ms, 190 candidate chunks; selection 0.099 ms, 982 words selected
- Selection decisions: NVDA_2024_10K_0212 selected, NVDA_2024_10K_0219 selected, NVDA_2024_10K_0233 selected, NVDA_2024_10K_0228 selected, NVDA_2024_10K_0038 limit, NVDA_2024_10K_0227 limit, NVDA_2024_10K_0037 limit, NVDA_2024_10K_0147 limit, NVDA_2024_10K_0159 limit, NVDA_2024_10K_0105 limit

**Selected context**

1. `NVDA_2024_10K_0212`, NVIDIA Corporation FY2024, score 0.794: "60 Table of Contents NVIDIA Corporation and Subsidiaries Notes to the Consolidated Financial Statements (Continued) Other information related to leases was as follows: Year Ended Jan 28, 2024 | Jan 29, 2023 | Jan 30, 2022 (In millions) Supplemental cash flows information Operating cash flows used for operating leases | $ | 286 | $ | 184 | $ | ..."
2. `NVDA_2024_10K_0219`, NVIDIA Corporation FY2024, score 0.767: "goodwill balances allocated to our Compute & Networking and Graphics reporting units of $ 4.0 billion and $ 370 million, respectively. Goodwill increased by $ 59 million in fiscal year 2024 from an immaterial acquisition and was allocated to our Compute & Networking reporting unit. During the fourth quarters of fiscal years 2024, 2023, and 2022, we completed our annual ..."
3. `NVDA_2024_10K_0233`, NVIDIA Corporation FY2024, score 0.762: "cancellation. Other non-inventory purchase obligations were $ 4.6 billion, which includes $ 3.5 billion of multi-year cloud service agreements, primarily to support our research and development efforts. 72 Table of Contents NVIDIA Corporation and Subsidiaries Notes to the Consolidated Financial Statements (Continued) Total future purchase commitments as of January 28, 2024 are as follows: Commitments (In millions) Fiscal Year: 2025 ..."
4. `NVDA_2024_10K_0228`, NVIDIA Corporation FY2024, score 0.743: "Deferred revenue primarily includes customer advances and deferrals related to support for hardware and software, license and development arrangements, and cloud services. $ 233 million and $ 35 million of the balance in fiscal 2024 and 2023 respectively, related to customer advances. Jan 28, 2024 | Jan 29, 2023 (In millions) Other Long-Term Liabilities: Income tax payable (1) | $ ..."

**Answer** (2906 ms)

> [1] NVIDIA spent $2,532 million on research and development in fiscal 2024.

## 3. Who does NVIDIA consider its main competitors?

- Filters: ticker `NVDA`, fiscal year `None`
- Retrieval: 2.24 ms, 248 candidate chunks; selection 0.116 ms, 896 words selected
- Selection decisions: NVDA_2024_10K_0102 selected, NVDA_2025_10K_0104 redundant (copy of NVDA_2024_10K_0102, J=0.76), NVDA_2024_10K_0107 selected, NVDA_2025_10K_0115 selected, NVDA_2024_10K_0110 redundant (copy of NVDA_2025_10K_0115, J=0.81), NVDA_2025_10K_0157 selected, NVDA_2025_10K_0112 limit, NVDA_2024_10K_0052 limit, NVDA_2025_10K_0055 limit, NVDA_2025_10K_0183 limit

**Selected context**

1. `NVDA_2024_10K_0102`, NVIDIA Corporation FY2024, score 0.700: "targeting GPUs and semiconductors associated with AI have subjected and may in the future subject downstream users of our products to additional restrictions on the use, resale, repair, or transfer of our products, negatively impacting our business and financial results. Controls could negatively impact our cost and/or ability to provide services such as NVIDIA AI cloud services and could impact ..."
2. `NVDA_2024_10K_0107`, NVIDIA Corporation FY2024, score 0.654: "for exports to D1 and D4 countries has been time-consuming and resulted in license conditions for countries outside China. The requirements have a disproportionate impact on NVIDIA and already have disadvantaged and may in the future 26 Table of Contents disadvantage NVIDIA against certain of our competitors who sell products that are not subject to the new restrictions or may ..."
3. `NVDA_2025_10K_0115`, NVIDIA Corporation FY2025, score 0.631: "a substantial portion of our products, which are warehoused in and distributed from Hong Kong. Export controls restricting our ability to sell data center GPUs may also negatively impact demand for our networking products used in servers containing our GPUs. The USG may also impose export controls on our networking products, such as high-speed network interconnects, to limit the ability ..."
4. `NVDA_2025_10K_0157`, NVIDIA Corporation FY2025, score 0.615: "down was an unfavorable impact of 2.3% in fiscal year 2025 and 2.7% in fiscal year 2024. Our inventory and capacity purchase commitments are based on forecasts of future customer demand and consider our third-party manufacturers' lead times and constraints. Our manufacturing lead times can be and have been long, and in some cases, extended beyond twelve months for some ..."

**Answer** (2121 ms)

> NVIDIA considers its competitors as those who sell products that are not subject to the new restrictions or may be able to acquire licenses for their products [2].

## 4. nvidea gaming revenue

*Why this question:* typo in the company name.

- Filters: ticker `None`, fiscal year `None`
- Retrieval: 5.79 ms, 762 candidate chunks; selection 0.093 ms, 963 words selected
- Selection decisions: NVDA_2024_10K_0146 selected, NVDA_2024_10K_0147 selected, NVDA_2024_10K_0145 selected, NVDA_2024_10K_0156 selected, NVDA_2024_10K_0250 limit, NVDA_2025_10K_0255 limit, NVDA_2025_10K_0144 limit, NVDA_2025_10K_0252 limit, MSFT_2025_10K_0117 limit, NVDA_2025_10K_0256 limit

**Selected context**

1. `NVDA_2024_10K_0146`, NVIDIA Corporation FY2024, score 0.900: "in the fiscal year. Gaming revenue for fiscal year 2024 was up 15%. The increase reflects higher sell-in to partners following the normalization of channel inventory levels and growing demand. Professional Visualization revenue for fiscal year 2024 was up 1%. Automotive revenue for the fiscal year 2024 was up 21%. The increase primarily reflected growth in self-driving platforms. Gross margin ..."
2. `NVDA_2024_10K_0147`, NVIDIA Corporation FY2024, score 0.886: "algorithms move to video transformers, and more cars are equipped with cameras, we expect NVIDIA’s automotive data center processing demand to grow significantly. We estimate that in fiscal year 2024, approximately 40% of Data Center revenue was for AI inference. In the fourth quarter of fiscal year 2024, large cloud providers represented more than half of our Data Center revenue, ..."
3. `NVDA_2024_10K_0145`, NVIDIA Corporation FY2024, score 0.845: "however, if the conflict is further extended, it could impact future product development, operations, and revenue or create other uncertainty for our business. 35 Table of Contents Fiscal Year 2024 Summary Year Ended Jan 28, 2024 | Jan 29, 2023 | Change ($ in millions, except per share data) Revenue | $ | 60,922 | $ | 26,974 | Up ..."
4. `NVDA_2024_10K_0156`, NVIDIA Corporation FY2024, score 0.772: "6.6 | (0.7) Net income | 48.9 | % | 16.2 | % Reportable Segments Revenue by Reportable Segments Year Ended Jan 28, 2024 | Jan 29, 2023 | $ Change | % Change ($ in millions) Compute & Networking | $ | 47,405 | $ | 15,068 | $ | 32,337 | 215 | % Graphics | 13,517 | ..."

**Answer** (2898 ms)

> Gaming revenue for fiscal year 2024 was $10.4 billion, up 15% from fiscal year 2023 [2].

## 5. What risks does AMD describe about export restrictions to China?

- Filters: ticker `AMD`, fiscal year `None`
- Retrieval: 2.72 ms, 242 candidate chunks; selection 0.097 ms, 934 words selected
- Selection decisions: AMD_2025_10K_0167 selected, AMD_2025_10K_0107 selected, AMD_2024_10K_0106 selected, AMD_2025_10K_0106 selected, AMD_2025_10K_0146 limit, AMD_2024_10K_0141 limit, AMD_2025_10K_0109 limit, AMD_2024_10K_0108 limit, AMD_2025_10K_0113 limit, AMD_2024_10K_0107 limit

**Selected context**

1. `AMD_2025_10K_0167`, Advanced Micro Devices, Inc. FY2025, score 0.800: "Subject to certain conditions, the warrant is exercisable through October 5, 2030. None of the warrant shares met the vesting or exercise conditions and the warrant had no impact to our financial statements for the year ended December 27, 2025. During the second quarter of fiscal year 2025, the Company recorded approximately $800 million of inventory and related charges on ..."
2. `AMD_2025_10K_0107`, Advanced Micro Devices, Inc. FY2025, score 0.790: "may limit our ability to sell certain products or technologies in these markets or to certain customers. Evolving U.S. government policy toward semiconductor exports, particularly in the context of national security and foreign policy priorities could adversely affect our business. In October 2023, the Bureau of Industry and Security (BIS) of the United States Department of Commerce issued requirements for ..."
3. `AMD_2024_10K_0106`, Advanced Micro Devices, Inc. FY2024, score 0.740: "requirements for certain advanced computing items that apply to the export of products classified ECCN 3A090 or 4A090 to a party headquartered in, or with an ultimate parent headquartered in, any of Country Groups D1, D4 or D5, including China. These controls prevent us from shipping certain AMD Instinct™ integrated circuits and certain AMD Versal™ FPGAs to China, or to ..."
4. `AMD_2025_10K_0106`, Advanced Micro Devices, Inc. FY2025, score 0.729: "increasing our expenses, damaging our reputation for actual or perceived non-compliance, or requiring us to alter our operations and products. The long-term effects of climate change on the global economy and the technology industry are unclear but could be severe. Additionally, we are or expect to be subject to various new or proposed climate-related disclosure requirements and we expect to ..."

**Answer** (3649 ms)

> AMD describes risks associated with export restrictions to China in [1], [2], and [3]. These risks include limitations on selling certain products or technologies to China, potential delays in shipments due to licensing requirements, and the possibility of losing sales if new products are deemed subject to licensing requirements. Additionally, evolving U.S. government policy towards semiconductor exports could adversely affect AMD's business. [1]

## 6. How does AMD describe its data center segment?

- Filters: ticker `AMD`, fiscal year `None`
- Retrieval: 1.99 ms, 236 candidate chunks; selection 0.075 ms, 927 words selected
- Selection decisions: AMD_2025_10K_0161 selected, AMD_2025_10K_0228 selected, AMD_2024_10K_0156 selected, AMD_2024_10K_0012 selected, AMD_2024_10K_0014 limit, AMD_2024_10K_0157 limit, AMD_2025_10K_0014 limit, AMD_2024_10K_0015 limit, AMD_2025_10K_0163 limit, AMD_2025_10K_0229 limit

**Selected context**

1. `AMD_2025_10K_0161`, Advanced Micro Devices, Inc. FY2025, score 0.965: "the other sections of this Annual Report on Form 10-K, “Part II, Item 8: Financial Statements and Supplementary Data.” Introduction In this section, we will describe the general financial condition and the results of operations of Advanced Micro Devices, Inc. and its wholly-owned subsidiaries (collectively, “us,” “our” or “AMD”), including a discussion of our results of operations for 2025 compared ..."
2. `AMD_2025_10K_0228`, Advanced Micro Devices, Inc. FY2025, score 0.880: "recognition of $ 79 million of goodwill. The financial results of these acquired businesses, which were not material, were included in the Company's Consolidated Statements of Operations from their respective dates of acquisition within the Data Center segment. Pro Forma Information Since the ZT Manufacturing Business, which represented the majority of ZT Systems’ operations, was classified as held for sale ..."
3. `AMD_2024_10K_0156`, Advanced Micro Devices, Inc. FY2024, score 0.875: "Item 7 of our Annual Report on Form 10-K for the fiscal year ended December 30, 2023. Overview In 2024, we delivered strong annual revenue growth with net revenue increasing 14% to $25.8 billion, compared to $22.7 billion in 2023. This growth was driven by the performance of our Data Center and Client segments. Data Center net revenue of $12.6 ..."
4. `AMD_2024_10K_0012`, Advanced Micro Devices, Inc. FY2024, score 0.863: "opportunity to make AMD the end-to-end AI leader based on the breadth of our technology and product portfolios. Our AI strategy is focused on three priorities. The first is delivering a broad portfolio of high-performance adaptive hardware and software solutions. The second is expanding the deep and collaborative partnerships we have established across the ecosystem to accelerate deployments of AMD ..."

**Answer** (4624 ms)

> AMD describes its data center segment as driving strong revenue growth with net revenue increasing 14% to $25.8 billion in 2024 [3], and further increasing by 32% to $16.6 billion in 2025 [1]. The segment's growth was primarily driven by higher sales of AMD Instinct™ GPUs and AMD EPYC™ CPUs in 2024 [3] and 5th generation AMD EPYC™ processors in 2025 [1].

## 7. What does AMD say about the acquisition of ZT Systems?

- Filters: ticker `AMD`, fiscal year `None`
- Retrieval: 3.76 ms, 401 candidate chunks; selection 0.075 ms, 856 words selected
- Selection decisions: AMD_2024_10K_0008 selected, AMD_2025_10K_0139 selected, AMD_2025_10K_0228 selected, AMD_2024_10K_0013 selected, AMD_2025_10K_0165 limit, AMD_2024_10K_0177 limit, AMD_2025_10K_0223 limit, AMD_2024_10K_0159 limit, AMD_2024_10K_0215 limit, AMD_2025_10K_0012 limit

**Selected context**

1. `AMD_2024_10K_0008`, Advanced Micro Devices, Inc. FY2024, score 0.875: "dividends in the near future; AMD’s ability to achieve its corporate responsibility initiatives; expected future AI technology trends and developments; the expected benefits of AMD’s acquisition of Silo AI Oy (Silo AI); AMD’s anticipated acquisition of ZT Group Int’l, Inc. (ZT Systems) and the anticipated timing of the transaction; AMD’s intention to seek a strategic partner to acquire ZT Systems' ..."
2. `AMD_2025_10K_0139`, Advanced Micro Devices, Inc. FY2025, score 0.820: "invested in businesses, and may continue to do so, that offer products, services and technologies that we believe will help expand our product offerings and services and grow our business in response to changing technologies, customer demands and competitive pressures. Acquisitions and joint ventures include numerous risks including, but not limited to: our inability to identify suitable opportunities in a ..."
3. `AMD_2025_10K_0228`, Advanced Micro Devices, Inc. FY2025, score 0.818: "recognition of $ 79 million of goodwill. The financial results of these acquired businesses, which were not material, were included in the Company's Consolidated Statements of Operations from their respective dates of acquisition within the Data Center segment. Pro Forma Information Since the ZT Manufacturing Business, which represented the majority of ZT Systems’ operations, was classified as held for sale ..."
4. `AMD_2024_10K_0013`, Advanced Micro Devices, Inc. FY2024, score 0.802: "center workloads. During the year, we completed the acquisition of Silo AI Oy (Silo AI), an AI lab based in Finland. The acquisition of Silo AI expanded our capability to accelerate development and deployment of AI models on AMD hardware. Silo AI has also developed a software stack used to train multiple state-of-the-art large language models (LLMs) on AMD Instinct ..."

**Answer** (2936 ms)

> AMD intends to seek a strategic partner to acquire ZT Systems' manufacturing business [2]. Additionally, the acquisition of ZT Systems is expected to close in the first half of fiscal year 2025, subject to certain regulatory approvals and other customary closing conditions [4].

## 8. How much did Microsoft Azure and other cloud services revenue grow in fiscal 2025?

- Filters: ticker `MSFT`, fiscal year `2025`
- Retrieval: 3.46 ms, 223 candidate chunks; selection 0.082 ms, 948 words selected
- Selection decisions: MSFT_2025_10K_0113 selected, MSFT_2025_10K_0105 selected, MSFT_2025_10K_0208 selected, MSFT_2025_10K_0116 selected, MSFT_2025_10K_0114 limit, MSFT_2025_10K_0112 limit, MSFT_2025_10K_0110 limit, MSFT_2025_10K_0115 limit, MSFT_2025_10K_0111 limit, MSFT_2025_10K_0104 limit

**Selected context**

1. `MSFT_2025_10K_0113`, Microsoft Corporation FY2025, score 0.880: "Surface and PC accessories Xbox content and services revenue growth | Revenue from Xbox content and services, comprising first- and third-party content (including games and in-game content), Xbox Game Pass and other subscriptions, Xbox Cloud Gaming, advertising, and other cloud services Search and news advertising revenue (ex TAC) growth | Revenue from search and news advertising excluding traffic acquisition costs ..."
2. `MSFT_2025_10K_0105`, Microsoft Corporation FY2025, score 0.864: "investing in our cloud-based services, including datacenter operations; designing, manufacturing, marketing, and selling our other products and services; and income taxes. Highlights from fiscal year 2025 compared with fiscal year 2024 included: Microsoft Cloud revenue increased 23% to $168.9 billion. Microsoft 365 Commercial products and cloud services revenue increased 14% driven by Microsoft 365 Commercial cloud revenue growth of 15%. ..."
3. `MSFT_2025_10K_0208`, Microsoft Corporation FY2025, score 0.805: "(a) | $ | 144,546 | $ | 124,704 | $ | 106,744 Other countries | 137,178 | 120,418 | 105,171 Total | $ | 281,724 | $ | 245,122 | $ | 211,915 Includes billings to OEMs and certain multinational organizations because of the nature of these businesses and the impracticability of determining the geographic source of the revenue. ..."
4. `MSFT_2025_10K_0116`, Microsoft Corporation FY2025, score 0.743: "all workloads. Operating income increased $10.1 billion or 17%. Cost of revenue increased $2.8 billion or 14% driven by growth in Microsoft 365 Commercial cloud. Gross margin increased $11.2 billion or 13% driven by growth in Microsoft 365 Commercial cloud. Gross margin percentage decreased slightly primarily driven by the impact of scaling our AI infrastructure, offset in part by efficiency ..."

**Answer** (2521 ms)

> Microsoft Azure and other cloud services revenue grew 34% in fiscal 2025 [1].

## 9. What does Microsoft say about its investments in artificial intelligence?

- Filters: ticker `MSFT`, fiscal year `None`
- Retrieval: 3.64 ms, 406 candidate chunks; selection 0.152 ms, 966 words selected
- Selection decisions: MSFT_2024_10K_0122 selected, MSFT_2024_10K_0060 selected, MSFT_2025_10K_0104 redundant (copy of MSFT_2024_10K_0122, J=0.79), MSFT_2024_10K_0203 selected, MSFT_2025_10K_0045 redundant (copy of MSFT_2024_10K_0060, J=0.83), MSFT_2024_10K_0006 selected, MSFT_2025_10K_0006 limit, MSFT_2024_10K_0012 limit, MSFT_2024_10K_0011 limit, MSFT_2024_10K_0256 limit

**Selected context**

1. `MSFT_2024_10K_0122`, Microsoft Corporation FY2024, score 0.730: "operations and financial condition of Microsoft Corporation. MD&A is provided as a supplement to, and should be read in conjunction with, our consolidated financial statements and the accompanying Notes to Financial Statements (Part II, Item 8 of this Form 10-K). This section generally discusses the results of our operations for the year ended June 30, 2024 compared to the year ..."
2. `MSFT_2024_10K_0060`, Microsoft Corporation FY2024, score 0.729: "of business models. A material part of our business involves cloud-based services available across the spectrum of computing devices. Our competitors continue to develop and deploy cloud-based services for consumers and business customers, and pricing and delivery models are evolving. We and our competitors are devoting significant resources to develop and deploy our cloud-based strategies. We are investing in artificial ..."
3. `MSFT_2024_10K_0203`, Microsoft Corporation FY2024, score 0.711: "results of Microsoft Corporation on an unaudited pro forma basis, as if the acquisition had been consummated on July 1, 2022: (In millions, except per share amounts) Year Ended June 30, | 2024 | 2023 Revenue | $ | 247,442 | $ | 219,790 Net income | 88,308 | 71,383 Diluted earnings per share | 11.82 | 9.55 These pro ..."
4. `MSFT_2024_10K_0006`, Microsoft Corporation FY2024, score 0.686: "that could cause actual results and events to differ materially in “Risk Factors,” “Management’s Discussion and Analysis of Financial Condition and Results of Operations,” and “Quantitative and Qualitative Disclosures About Market Risk” (Part II, Item 7A of this Form 10-K). Readers are cautioned not to place undue reliance on forward-looking statements, which speak only as of the date they are ..."

**Answer** (2214 ms)

> Microsoft invests in artificial intelligence across the entire company and infuses generative AI capabilities into its consumer and commercial offerings [2].

## 10. microsft cloud revenue

*Why this question:* typo in the company name.

- Filters: ticker `None`, fiscal year `None`
- Retrieval: 5.61 ms, 820 candidate chunks; selection 0.072 ms, 918 words selected
- Selection decisions: MSFT_2024_10K_0129 selected, MSFT_2025_10K_0111 redundant (copy of MSFT_2024_10K_0129, J=0.56), MSFT_2025_10K_0113 selected, MSFT_2024_10K_0123 selected, MSFT_2025_10K_0114 selected, MSFT_2024_10K_0132 limit, MSFT_2025_10K_0105 limit, MSFT_2025_10K_0116 limit, MSFT_2024_10K_0128 limit, MSFT_2025_10K_0208 limit

**Selected context**

1. `MSFT_2024_10K_0129`, Microsoft Corporation FY2024, score 0.900: "our commercial business and include leading indicators of future performance. Commercial remaining performance obligation | Commercial portion of revenue allocated to remaining performance obligations, which includes unearned revenue and amounts that will be invoiced and recognized as revenue in future periods Microsoft Cloud revenue and revenue growth | Revenue from Azure and other cloud services, Office 365 Commercial, the commercial ..."
2. `MSFT_2025_10K_0113`, Microsoft Corporation FY2025, score 0.867: "Surface and PC accessories Xbox content and services revenue growth | Revenue from Xbox content and services, comprising first- and third-party content (including games and in-game content), Xbox Game Pass and other subscriptions, Xbox Cloud Gaming, advertising, and other cloud services Search and news advertising revenue (ex TAC) growth | Revenue from search and news advertising excluding traffic acquisition costs ..."
3. `MSFT_2024_10K_0123`, Microsoft Corporation FY2024, score 0.859: "a global audience; and designing and selling devices. Our most significant expenses are related to compensating employees; supporting and investing in our cloud-based services, including datacenter operations; designing, manufacturing, marketing, and selling our other products and services; and income taxes. Highlights from fiscal year 2024 compared with fiscal year 2023 included: Microsoft Cloud revenue increased 23% to $137.4 billion. Office ..."
4. `MSFT_2025_10K_0114`, Microsoft Corporation FY2025, score 0.858: "margin percentage decreased slightly driven by Intelligent Cloud, offset in part by More Personal Computing. Microsoft Cloud gross margin percentage decreased to 69% driven by the impact of scaling our AI infrastructure, offset in part by efficiency gains in Azure. Operating expenses increased $3.8 billion or 6% driven by investments in cloud and AI engineering and Gaming, including the impact ..."

**Answer** (3474 ms)

> Microsoft Cloud revenue increased 23% to $137.4 billion in fiscal year 2024 [3]. In fiscal year 2025, Microsoft Cloud revenue increased 21% to $106,265 million [4].

## 11. What does Apple say about iPhone net sales in fiscal 2025?

- Filters: ticker `AAPL`, fiscal year `2025`
- Retrieval: 2.80 ms, 144 candidate chunks; selection 0.074 ms, 964 words selected
- Selection decisions: AAPL_2025_10K_0084 selected, AAPL_2025_10K_0083 selected, AAPL_2025_10K_0108 selected, AAPL_2025_10K_0107 selected, AAPL_2025_10K_0065 limit, AAPL_2025_10K_0095 limit, AAPL_2025_10K_0086 limit, AAPL_2025_10K_0081 limit, AAPL_2025_10K_0085 limit, AAPL_2025_10K_0096 limit

**Selected context**

1. `AAPL_2025_10K_0084`, Apple Inc. FY2025, score 0.829: "compared to 2024 primarily due to higher net sales of iPhone, Services and Mac. Apple Inc. | 2025 Form 10-K | 22 Products and Services Performance The following table shows net sales by category for 2025, 2024 and 2023 (dollars in millions): 2025 | Change | 2024 | Change | 2023 iPhone | $ | 209,586 | 4 | % ..."
2. `AAPL_2025_10K_0083`, Apple Inc. FY2025, score 0.762: "services, all of which can further adversely affect the Company’s business and results of operations. Segment Operating Performance The following table shows net sales by reportable segment for 2025, 2024 and 2023 (dollars in millions): 2025 | Change | 2024 | Change | 2023 Americas | $ | 178,353 | 7 | % | $ | 167,045 | 3 | ..."
3. `AAPL_2025_10K_0108`, Apple Inc. FY2025, score 0.681: "2024 and 2023, except in Greater China, where iPhone revenue represented a moderately higher proportion of net sales. As of September 27, 2025 and September 28, 2024, the Company had total deferred revenue of $ 13.7 billion and $ 12.8 billion, respectively. As of September 27, 2025, the Company expects 66 % of total deferred revenue to be realized in ..."
4. `AAPL_2025_10K_0107`, Apple Inc. FY2025, score 0.680: "product, retains inventory risk for tangible products or has the responsibility for ensuring acceptability of the product. For third-party applications sold through the App Store, the Company does not obtain control of the product before transferring it to the customer. Therefore, the Company accounts for all third-party application–related sales on a net basis by recognizing in Services net sales only ..."

**Answer** (3336 ms)

> Apple says iPhone net sales increased during 2025 compared to 2024 primarily due to higher net sales of Pro models [1].

## 12. How does Apple describe its services revenue?

- Filters: ticker `AAPL`, fiscal year `None`
- Retrieval: 2.20 ms, 226 candidate chunks; selection 0.096 ms, 900 words selected
- Selection decisions: AAPL_2024_10K_0039 selected, AAPL_2025_10K_0039 redundant (copy of AAPL_2024_10K_0039, J=0.61), AAPL_2024_10K_0103 selected, AAPL_2024_10K_0100 selected, AAPL_2024_10K_0060 selected, AAPL_2025_10K_0107 limit, AAPL_2025_10K_0051 limit, AAPL_2025_10K_0103 limit, AAPL_2024_10K_0081 limit, AAPL_2025_10K_0052 limit

**Selected context**

1. `AAPL_2024_10K_0039`, Apple Inc. FY2024, score 0.850: "certain products or services, or otherwise have a material adverse impact on the Company’s business, results of operations and financial condition. Apple Inc. | 2024 Form 10-K | 9 The Company’s future performance depends in part on support from third-party software developers. The Company believes decisions by customers to purchase its hardware products depend in part on the availability of ..."
2. `AAPL_2024_10K_0103`, Apple Inc. FY2024, score 0.807: "Company considers multiple factors when determining whether it obtains control of third-party products, including evaluating if it can establish the price of the product, retains inventory risk for tangible products or has the responsibility for ensuring acceptability of the product. For third-party applications sold through the App Store, the Company does not obtain control of the product before transferring it ..."
3. `AAPL_2024_10K_0100`, Apple Inc. FY2024, score 0.788: "foreign earnings created by the TCJA. Leases The Company combines and accounts for lease and nonlease components as a single lease component for leases of corporate, data center and retail facilities. Apple Inc. | 2024 Form 10-K | 34 Note 2 – Revenue The Company recognizes revenue at the amount to which it expects to be entitled when control of ..."
4. `AAPL_2024_10K_0060`, Apple Inc. FY2024, score 0.777: "or may become subject to investigations and litigation that, if resolved against those other companies, could materially adversely affect the Company’s commercial relationships with those business partners and materially adversely affect the Company’s business, results of operations and financial condition. For example, the Company earns revenue from licensing arrangements with Google LLC and other companies to offer their search services ..."

**Answer** (4977 ms)

> Apple describes its services revenue as recognizing revenue at the amount to which it expects to be entitled when control of the products or services is transferred to its customers [3]. Services net sales include amortization of the deferred value of services bundled in the sales price of certain products [2]. Services net sales are disaggregated by significant products and services for 2024, 2023, and 2022, showing figures for iPhone, Mac, iPad, Wearables, Home and Accessories, and Services [2]. Revenue from services is recognized over time as services are delivered [3].

## 13. How many employees does Apple have?

*Why this question:* the filing says 'the Company', not 'Apple'.

- Filters: ticker `AAPL`, fiscal year `None`
- Retrieval: 1.43 ms, 199 candidate chunks; selection 0.079 ms, 901 words selected
- Selection decisions: AAPL_2025_10K_0043 selected, AAPL_2025_10K_0047 selected, AAPL_2025_10K_0120 selected, AAPL_2024_10K_0021 selected, AAPL_2024_10K_0122 limit, AAPL_2024_10K_0055 limit, AAPL_2024_10K_0123 limit, AAPL_2025_10K_0021 limit, AAPL_2025_10K_0015 limit, AAPL_2024_10K_0017 limit

**Selected context**

1. `AAPL_2025_10K_0043`, Apple Inc. FY2025, score 1.000: "navigate changes effectively in order to achieve its strategic initiatives. Laws and regulations, including immigration, labor and employment laws and export controls, among others, can materially adversely affect the Company’s ability to recruit and retain a highly skilled, global workforce. If the Company does not effectively manage changing workforce dynamics and regulatory requirements, it could materially adversely affect the Company’s ..."
2. `AAPL_2025_10K_0047`, Apple Inc. FY2025, score 0.900: "operations. Attacks can impair the Company’s ability to attract and retain customers for its products and services, affect its stock price, damage commercial relationships, and expose the Company to litigation or government investigations, potentially resulting in penalties, fines or judgments. Globally, attacks are expected to continue accelerating in both frequency and sophistication with increasing use by actors of tools and ..."
3. `AAPL_2025_10K_0120`, Apple Inc. FY2025, score 0.671: "temporary differences. Apple Inc. | 2025 Form 10-K | 41 Uncertain Tax Positions As of September 27, 2025, the total amount of gross unrecognized tax benefits was $ 23.2 billion, of which $ 10.6 billion, if recognized, would impact the Company’s effective tax rate. As of September 28, 2024, the total amount of gross unrecognized tax benefits was $ 22.0 ..."
4. `AAPL_2024_10K_0021`, Apple Inc. FY2024, score 0.662: "economic conditions can have a significant impact on the Company’s suppliers, contract manufacturers, logistics providers, distributors, cellular network carriers and other channel partners, and developers. Potential outcomes include financial instability; inability to obtain credit to finance business operations; and insolvency. Adverse economic conditions can also lead to increased credit and collectibility risk on the Company’s trade receivables; the failure of ..."

**Answer** (1869 ms)

> The provided filings do not contain this information. [1]

## 14. What risks does Apple describe about manufacturing in China?

- Filters: ticker `AAPL`, fiscal year `None`
- Retrieval: 1.78 ms, 226 candidate chunks; selection 0.095 ms, 971 words selected
- Selection decisions: AAPL_2024_10K_0065 selected, AAPL_2025_10K_0034 selected, AAPL_2025_10K_0035 selected, AAPL_2024_10K_0064 selected, AAPL_2024_10K_0030 limit, AAPL_2025_10K_0130 limit, AAPL_2024_10K_0024 limit, AAPL_2024_10K_0081 limit, AAPL_2024_10K_0129 limit, AAPL_2025_10K_0030 limit

**Selected context**

1. `AAPL_2024_10K_0065`, Apple Inc. FY2024, score 0.755: "or failure of one of the Company’s logistics, supply or manufacturing partners. Apple Inc. | 2024 Form 10-K | 15 The Company’s financial performance is subject to risks associated with changes in the value of the U.S. dollar relative to local currencies. The Company’s primary exposure to movements in foreign exchange rates relates to non–U.S. dollar–denominated sales, cost of sales ..."
2. `AAPL_2025_10K_0034`, Apple Inc. FY2025, score 0.748: "affected the Company’s ability to obtain sufficient quantities of components and products on commercially reasonable terms, or at all. Such disruptions could occur in the future. Additionally, the Company’s new products often utilize custom components available from only one source. When a component or product uses new technologies, initial capacity constraints may exist until the suppliers’ yields have matured or ..."
3. `AAPL_2025_10K_0035`, Apple Inc. FY2025, score 0.734: "price. Apple Inc. | 2025 Form 10-K | 8 The Company’s products and services may be affected from time to time by design and manufacturing defects that could materially adversely affect the Company’s business and result in harm to the Company’s reputation. The Company offers complex hardware and software products and services that can be affected by design and manufacturing ..."
4. `AAPL_2024_10K_0064`, Apple Inc. FY2024, score 0.726: "for the Company’s services; the Company’s ability to manage product quality and warranty costs effectively; shifts in the mix of products and services, or in the geographic, currency or channel mix, including to the extent that regulatory changes require the Company to modify its product and service offerings; fluctuations in foreign exchange rates; inflation and other macroeconomic pressures; and the ..."

**Answer** (1736 ms)

> The provided filings do not contain this information. [1]

## 15. What are Alphabet's main sources of revenue?

- Filters: ticker `GOOGL`, fiscal year `None`
- Retrieval: 1.04 ms, 84 candidate chunks; selection 0.108 ms, 979 words selected
- Selection decisions: GOOGL_2025_10K_0184 selected, GOOGL_2024_10K_0197 redundant (copy of GOOGL_2025_10K_0184, J=0.81), GOOGL_2024_10K_0008 selected, GOOGL_2024_10K_0025 selected, GOOGL_2025_10K_0119 selected, GOOGL_2024_10K_0103 limit, GOOGL_2024_10K_0129 limit, GOOGL_2025_10K_0111 limit, GOOGL_2025_10K_0100 limit, GOOGL_2025_10K_0185 limit

**Selected context**

1. `GOOGL_2025_10K_0184`, Alphabet Inc. FY2025, score 0.700: "customers utilize services. Revenue backlog includes related deferred revenue currently recorded as well as amounts that will be invoiced in future periods, and excludes contracts with an original expected term of one year or less and cancellable contracts. Deferred Revenues We record deferred revenues when cash payments are received or due in advance of our performance, including amounts which are ..."
2. `GOOGL_2024_10K_0008`, Alphabet Inc. FY2024, score 0.667: "hedging activities under our foreign exchange risk management program; • the amount and timing of revenue recognition from customer contracts with commitments for performance obligations, including our estimate of the remaining amount of commitments and when we expect to recognize revenue; • our expectation that our capital expenditures will increase, including our expected spend and the expected increase in our ..."
3. `GOOGL_2024_10K_0025`, Alphabet Inc. FY2024, score 0.628: "Smart Reply, Smart Compose, and malware and phishing protection in Gmail. Now, Gemini for Google Workspace brings our AI-powered agents into Gmail, Docs, Sheets and more to help users write, organize, visualize, accelerate workflows, and have richer meetings. Other Bets Across Alphabet, we are also using technology to try to solve big problems that affect a wide variety of industries, ..."
4. `GOOGL_2025_10K_0119`, Alphabet Inc. FY2025, score 0.401: "of revenues, including TAC (in millions, except percentages): Year Ended December 31, 2024 | 2025 TAC | $ | 54,900 | $ | 59,926 Other cost of revenues | 91,406 | 102,609 Total cost of revenues | $ | 146,306 | $ | 162,535 Total cost of revenues as a percentage of revenues | 42 | % | 40 | ..."

**Answer** (3947 ms)

> Alphabet's main sources of revenue include Google Cloud and Google subscriptions, platforms, and devices [1]. Revenue from TAC (Transaction Advertising Cost) increased significantly from 2024 to 2025, contributing to overall cost of revenues [4]. Other cost of revenues also saw an increase, primarily due to content acquisition costs, depreciation expense, and other technical infrastructure operations costs [4].

## 16. What does Google say about YouTube advertising revenue?

- Filters: ticker `GOOGL`, fiscal year `None`
- Retrieval: 3.55 ms, 359 candidate chunks; selection 0.095 ms, 930 words selected
- Selection decisions: GOOGL_2024_10K_0114 selected, GOOGL_2025_10K_0106 redundant (copy of GOOGL_2024_10K_0114, J=0.97), GOOGL_2024_10K_0172 selected, GOOGL_2024_10K_0116 selected, GOOGL_2025_10K_0108 redundant (copy of GOOGL_2024_10K_0116, J=0.92), GOOGL_2024_10K_0043 selected, GOOGL_2025_10K_0101 limit, GOOGL_2024_10K_0118 limit, GOOGL_2024_10K_0109 limit, GOOGL_2025_10K_0110 limit

**Selected context**

1. `GOOGL_2024_10K_0114`, Alphabet Inc. FY2024, score 0.820: "fluctuations in our revenues have been and may continue to be affected by a combination of factors, including: • changes in foreign currency exchange rates; • changes in pricing, such as those resulting from changes in fee structures, discounts, and customer incentives; • general economic conditions and various external dynamics, including geopolitical events, regulations, and other measures and their effect ..."
2. `GOOGL_2024_10K_0172`, Alphabet Inc. FY2024, score 0.808: "balances and transactions have been eliminated. Use of Estimates Preparation of consolidated financial statements in conformity with GAAP requires us to make estimates and assumptions that affect the amounts reported and disclosed in the financial statements and the accompanying notes. Actual results could differ materially from these estimates due to uncertainties. On an ongoing basis, we evaluate our estimates, including ..."
3. `GOOGL_2024_10K_0116`, Alphabet Inc. FY2024, score 0.793: "As our business evolves, we periodically review, refine, and update our methodologies for monitoring, gathering, and counting the number of paid clicks and the number of impressions, and for identifying the revenues generated by the corresponding click and impression activity. Fluctuations in our advertising revenues, as well as the change in paid clicks and cost-per-click on Google Search & other ..."
4. `GOOGL_2024_10K_0043`, Alphabet Inc. FY2024, score 0.787: "and demand for our products and services. Because all of these investment areas are inherently risky, no assurance can be given that such strategies and offerings will be successful or will not harm our reputation, financial condition, and operating results. Our revenue growth rate could decline over time, and we may experience downward pressure on our operating margin in the ..."

**Answer** (1974 ms)

> YouTube advertising revenue is part of Google's Google advertising revenues, which include revenues generated on YouTube properties [2].

## 17. What legal or antitrust matters does Alphabet describe?

- Filters: ticker `GOOGL`, fiscal year `None`
- Retrieval: 2.25 ms, 340 candidate chunks; selection 0.108 ms, 954 words selected
- Selection decisions: GOOGL_2024_10K_0225 selected, GOOGL_2025_10K_0214 redundant (copy of GOOGL_2024_10K_0225, J=0.73), GOOGL_2025_10K_0071 selected, GOOGL_2025_10K_0120 selected, GOOGL_2025_10K_0150 selected, GOOGL_2025_10K_0025 limit, GOOGL_2025_10K_0121 limit, GOOGL_2025_10K_0132 limit, GOOGL_2025_10K_0114 limit, GOOGL_2025_10K_0218 limit

**Selected context**

1. `GOOGL_2024_10K_0225`, Alphabet Inc. FY2024, score 0.880: "estimated, we disclose the reasonably possible loss. We evaluate developments in our legal matters that could affect the amount of liability that has been previously accrued, and the matters and related reasonably possible losses disclosed, and make adjustments as appropriate. Certain outstanding matters seek speculative, substantial or indeterminate monetary amounts, substantial changes to our business practices and products, or structural ..."
2. `GOOGL_2025_10K_0071`, Alphabet Inc. FY2025, score 0.826: "continue to be subject to claims, lawsuits, regulatory and government inquiries and investigations, enforcement actions, consent orders, and other forms of regulatory scrutiny and legal liability, including competition matters, that could harm our business, reputation, financial condition, and operating results. We are subject to claims, lawsuits, regulatory and government inquiries and investigations, other proceedings, and orders involving competition, intellectual property, ..."
3. `GOOGL_2025_10K_0120`, Alphabet Inc. FY2025, score 0.697: "61,087 Research and development expenses as a percentage of revenues | 14 | % | 15 | % Research and development expenses increased $11.8 billion from 2024 to 2025, primarily driven by increases in employee compensation expenses of $6.9 billion and depreciation expense of $2.4 billion. The increase in employee compensation expenses was primarily driven by an increase in SBC ..."
4. `GOOGL_2025_10K_0150`, Alphabet Inc. FY2025, score 0.650: "external legal counsel addressing the matters, meeting with internal legal counsel to discuss the allegations, and obtaining a representation letter from management on these matters. We also evaluated the Company’s disclosures in relation to these matters. /s/ Ernst & Young LLP We have served as the Company's auditor since 1999. San Jose, California February 4, 2026 46. Table of Contents ..."

**Answer** (5024 ms)

> Alphabet describes antitrust matters including formal and informal inquiries and investigations by regulatory authorities and private parties in the U.S., Europe, and other jurisdictions globally [1]. Specifically, it mentions a € 2.4 billion fine imposed by the EC for certain actions taken by Google relating to its display and ranking of shopping search results and ads infringing European antitrust laws [1]. Additionally, it is subject to antitrust lawsuits about aspects of its business, including its advertising technologies and practices, the operation and distribution of Google Search, and the operation and distribution of Android operating system and Play Store [2].

## 18. Which companies depend on TSMC to manufacture their chips?

*Why this question:* no company filter, cross filing.

- Filters: ticker `None`, fiscal year `None`
- Retrieval: 2.43 ms, 399 candidate chunks; selection 0.089 ms, 910 words selected
- Selection decisions: AMD_2025_10K_0073 selected, AMD_2024_10K_0091 selected, AMD_2025_10K_0092 selected, GOOGL_2025_10K_0041 selected, AMD_2024_10K_0090 limit, AMD_2025_10K_0051 limit, AMD_2024_10K_0050 limit, GOOGL_2024_10K_0048 limit, GOOGL_2025_10K_0063 limit, NVDA_2024_10K_0030 limit

**Selected context**

1. `AMD_2025_10K_0073`, Advanced Micro Devices, Inc. FY2025, score 0.880: "and on our financial condition. In addition, if we are unable to meet customer demand due to fluctuating or late supply from our manufacturing suppliers, it could result in lost sales and have a material adverse effect on our business. For example, if TSMC is not able to manufacture wafers for our microprocessor and GPU products at 7 nm or ..."
2. `AMD_2024_10K_0091`, Advanced Micro Devices, Inc. FY2024, score 0.708: "intellectual property in certain regions or products, our business could be materially adversely affected. We depend on third-party companies for the design, manufacture and supply of motherboards, software, memory and other computer platform components to support our business and products. We depend on third-party companies for the design, manufacture and supply of motherboards, graphics cards, software (e.g., BIOS, operating systems, ..."
3. `AMD_2025_10K_0092`, Advanced Micro Devices, Inc. FY2025, score 0.691: "incorporate into our software or hardware. The design requirements necessary to meet customer demand for more features and greater functionality from semiconductor products may exceed the capabilities of the third-party intellectual property or development or testing tools available to us. If the third-party intellectual property that we use becomes unavailable, is not available with required functionality or performance in the ..."
4. `GOOGL_2025_10K_0041`, Alphabet Inc. FY2025, score 0.688: "or products or objectionable practices by advertisers, or otherwise to adequately address user concerns, our users may lose confidence in our brands. Furthermore, failure to maintain and enhance our brands could harm our business, reputation, financial condition, and operating results. Our success will depend largely on our ability to remain a technology leader and continue to provide high-quality, trustworthy, innovative ..."

**Answer** (2132 ms)

> TSMC manufactures chips for AMD [1]. TSMC also manufactures chips for other companies, including certain of AMD's competitors [1].

## 19. What is Tesla revenue from electric vehicles?

*Why this question:* out of corpus: no Tesla filing.

- Filters: ticker `None`, fiscal year `None`
- Retrieval: 2.78 ms, 536 candidate chunks; selection 0.092 ms, 924 words selected
- Selection decisions: NVDA_2024_10K_0148 selected, NVDA_2025_10K_0026 selected, NVDA_2024_10K_0024 redundant (copy of NVDA_2025_10K_0026, J=0.64), NVDA_2025_10K_0251 selected, NVDA_2025_10K_0252 selected, AMD_2025_10K_0188 limit, AMD_2024_10K_0178 limit, AMD_2024_10K_0170 limit, AMD_2025_10K_0178 limit, AAPL_2025_10K_0052 limit

**Selected context**

1. `NVDA_2024_10K_0148`, NVIDIA Corporation FY2024, score 0.850: "Ada Lovelace architecture, and announced NVIDIA Omniverse Cloud, a fully managed service running in Microsoft Azure, for the development and deployment of industrial metaverse applications. Automotive revenue for fiscal year 2024 was $1.1 billion, up 21% from fiscal year 2023. In Automotive, we announced a partnership with MediaTek, which will develop mainstream automotive systems on chips for global OEMs integrating ..."
2. `NVDA_2025_10K_0026`, NVIDIA Corporation FY2025, score 0.592: "sharing of gameplay. Our Studio drivers enhance and accelerate a number of popular creative applications. Omniverse is real-time 3D design collaboration and virtual world simulation software that empowers artists, designers, and creators to connect and collaborate in leading design applications. We also enable interactive graphics applications - such as games, movie and photo editing and design software - to be ..."
3. `NVDA_2025_10K_0251`, NVIDIA Corporation FY2025, score 0.537: "dividends is subject to our Board of Directors' continuing determination that the declaration of dividends is in the best interests of our shareholders. Note 15 - Employee Retirement Plans We provide tax-qualified defined contribution plans to eligible employees in the U.S. and certain other countries. Our contribution expense for fiscal years 2025, 2024, and 2023 was $ 314 million, $ ..."
4. `NVDA_2025_10K_0252`, NVIDIA Corporation FY2025, score 0.497: "to our CODM. The Compute & Networking segment includes our Data Center accelerated computing platforms and AI solutions and software; networking; automotive platforms and autonomous and electric vehicle solutions; Jetson for robotics and other embedded platforms; and DGX Cloud computing services. The Graphics segment includes GeForce GPUs for gaming and PCs, the GeForce NOW game streaming service and related infrastructure, ..."

**Answer** (1789 ms)

> The provided filings do not contain this information.

## 20. What is the outlook?

*Why this question:* vague question.

- Filters: ticker `None`, fiscal year `None`
- Retrieval: 0.13 ms, 11 candidate chunks; selection 0.098 ms, 892 words selected
- Selection decisions: MSFT_2025_10K_0013 selected, MSFT_2025_10K_0134 selected, MSFT_2024_10K_0154 redundant (copy of MSFT_2025_10K_0134, J=0.96), MSFT_2024_10K_0181 selected, MSFT_2024_10K_0153 selected, MSFT_2025_10K_0133 limit, MSFT_2024_10K_0024 limit, MSFT_2025_10K_0160 limit, AMD_2024_10K_0140 limit, MSFT_2025_10K_0014 limit

**Selected context**

1. `MSFT_2025_10K_0013`, Microsoft Corporation FY2025, score 1.000: "such as frontline workers, small and medium businesses, and growth markets, as well as add AI-enabled tools, features, and agentic scenarios to our core product and service offerings across communication, collaboration, analytics, security, compliance, and other AI business productivity categories. Microsoft 365 Commercial revenue is mainly affected by a combination of continued installed base growth and average revenue per user ..."
2. `MSFT_2025_10K_0134`, Microsoft Corporation FY2025, score 0.990: "this judgment, we employ a systematic methodology that considers available quantitative and qualitative evidence in evaluating potential impairment of our investments. In addition, we consider specific adverse conditions related to the financial health of, and business outlook for, the investee. If we have plans to sell the security or it is more likely than not that we will be required ..."
3. `MSFT_2024_10K_0181`, Microsoft Corporation FY2024, score 0.968: "nature and because such marketable securities represent the investment of cash that is available for current operations. 65 PART II Item 8 Debt investments are classified as available-for-sale and realized gains and losses are recorded using the specific identification method. Changes in fair value, excluding credit losses and impairments, are recorded in other comprehensive income. Fair value is calculated based ..."
4. `MSFT_2024_10K_0153`, Microsoft Corporation FY2024, score 0.967: "geographic region in determining the SSP. Due to the various benefits from and the nature of our SA program, judgment is required to assess the pattern of delivery, including the exercise pattern of certain benefits across our portfolio of customers. Our products are generally sold with a right of return, we may provide other credits or incentives, and in certain ..."

**Answer** (4287 ms)

> The outlook is evaluated through a systematic methodology considering available quantitative and qualitative evidence in evaluating potential impairment of investments [1]. Judgment is applied to assess the pattern of delivery for the SA program, requiring significant judgment due to the benefits and nature of the program [1]. Impairment of investment securities is reviewed quarterly for credit losses and impairment, with a systematic methodology employed to evaluate potential impairment [1]. The judgment involved in assessing the pattern of delivery for the SA program and the evaluation of potential impairment of investments require significant judgment [1].

## 21. How did share repurchases change in fiscal 2025?

*Why this question:* fiscal year filter but no company.

- Filters: ticker `None`, fiscal year `2025`
- Retrieval: 4.63 ms, 721 candidate chunks; selection 0.075 ms, 886 words selected
- Selection decisions: MSFT_2025_10K_0103 selected, MSFT_2025_10K_0102 selected, MSFT_2025_10K_0129 selected, NVDA_2025_10K_0170 selected, NVDA_2025_10K_0231 limit, NVDA_2025_10K_0232 limit, NVDA_2025_10K_0142 limit, NVDA_2025_10K_0169 limit, NVDA_2025_10K_0141 limit, NVDA_2025_10K_0171 limit

**Selected context**

1. `MSFT_2025_10K_0103`, Microsoft Corporation FY2025, score 0.880: "the fourth quarter of fiscal year 2025. Refer to Note 15 – Stockholders’ Equity of the Notes to Financial Statements (Part II, Item 8 of this Form 10-K) for further discussion regarding share repurchases and dividends. RECENT SALES OF UNREGISTERED SECURITIES In May 2025, as consideration for the acquisition of a business, we issued 117,623 shares of common stock to ..."
2. `MSFT_2025_10K_0102`, Microsoft Corporation FY2025, score 0.844: "448.01 | 2,360,700 | 58,293 June 1, 2025 – June 30, 2025 | 1,979,017 | 476.78 | 1,979,017 | 57,349 7,520,493 | 7,520,493 All share repurchases were made using cash resources. Our share repurchases may occur through open market purchases or pursuant to a Rule 10b5-1 trading plan. The above table excludes shares repurchased to settle employee tax withholding related ..."
3. `MSFT_2025_10K_0129`, Microsoft Corporation FY2025, score 0.836: "are not presented as construction commitments above. 44 PART II Item 7 Income Taxes As a result of the TCJA, we are required to pay a one-time transition tax on deferred foreign income not previously subject to U.S. income tax. Under the TCJA, the transition tax is payable in interest-free installments over eight years, with 8% due in each of ..."
4. `NVDA_2025_10K_0170`, NVIDIA Corporation FY2025, score 0.818: "7 of the Notes to the Consolidated Financial Statements in Part IV, Item 15 of this Annual Report on Form 10-K for additional information. Except for approximately $1.7 billion of cash, cash equivalents, and marketable securities held outside the U.S. for which we have not accrued any related foreign or state taxes if we repatriate these amounts to the U.S., ..."

**Answer** (3192 ms)

> Microsoft Corporation's share repurchases increased from $12.0 billion in fiscal year 2024 to $13.0 billion in fiscal year 2025 [2].
