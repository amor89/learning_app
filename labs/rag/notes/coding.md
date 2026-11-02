# Open-ended coding

## Codeframe

Open-ended answers to "What could we improve?" are coded into four themes: Price, Service, Product and Other. The codeframe is versioned. Version 3 has been in use since wave W10.

## Model-assisted coding

A language model proposes one theme per answer, with a confidence between 0 and 1. Answers with a confidence below 0.7, or with a reply that fails validation twice, go to a human coder. The prompt version and the model ID are stored with every label.

## Quality control

Each wave, a human coder recodes a random 5% sample of model-coded answers. If agreement falls below 85%, model coding stops until the prompt is reviewed.
