# Demo data — fictional, for testing only

Every brand, product, price and fact in this folder is **made up**. The brands
(Aurelyn, Brisalo, Kovalt, Nimbrex, Tavora, Zentro) do not exist, and the facts are
synthetic. They say nothing about any real company or product. Any resemblance to a
real brand name is accidental. Source URLs point at `example.com` on purpose.

| File | Contents |
|------|----------|
| `brands.csv` | 6 fictional earbud brands |
| `brand_aliases.csv` | Other names each brand may appear under in an answer |
| `brand_facts.csv` | Synthetic facts: prices per market (IN in INR, US in USD), battery life with conditions, ANC, IP rating, warranty per market, release year |
| `prompts.csv` | 6 shopping prompts in category `earbuds`, each tied to a market |
| `eval_set.json` | 16 hand-written AI-style answers (12 `dev`, 4 `holdout`) with gold claims: exact quote, label, cited fact IDs |

The eval answers include deliberate traps: market (US warranty quoted for India),
conditions (ANC-off battery quoted as ANC-on), comparison direction, a similar model
(Air 2 vs Air 2 Pro), currency with no matching fact, and missing evidence that must be
labelled `unknown`, not `contradicted`.

Check that every gold quote is in its answer and every cited fact exists:

```
auditor check-eval
```

Load the catalogue and prompts into the database at `DATABASE_URL`:

```
auditor seed
```
