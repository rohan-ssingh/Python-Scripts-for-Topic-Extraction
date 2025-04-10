All four approaches were each benchmarked on 4 different documents of varying lengths. The data is as follows:


Doc #1 False Positive	Doc #1 False Negative	Doc #2 False Positive	Doc #2 False Negative	Doc #3 False Positive	Doc #3 False Negative	Doc #4 False Positive	Doc #4 False Negative

Standard Model Standalone	0%	28.57%	20%	65.22%	11.11%	55.56%	0%	25%
								
Standard Model Deduplication	0%	28.57%	22.22%	69.22%	0%	50%	20%	33.33%
								
New Approach Standalone	0%	28.57%	48.00%	46%	12.50%	26.32%	9.09%	16.67%

New Approach Deduplication	12.50%	0%	26.32%	39.13%	18.75%	27.78%	0.00%	16.67%

Final Conclusions:

Standard Model Standalone
The topics that are extracted are usually accurate however, the approach is not able to capture all the important topics within a document (particularly larger-sized documents).

Standard Model with Deduplication
Slight improvements in FPR compared with standalone. However, the approach also suffered in detecting all of the relevant topics in larger-sized documents.

New Approach Standalone
Reduced FNR compared with standard models. However, the approach displayed a higher FPR (could be attributed to duplicate values).

New Approach with Deduplication
Best performer overall. Improvements in FPR compared to standalone new approach.
