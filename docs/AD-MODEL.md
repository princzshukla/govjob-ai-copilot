# Ad model — policy, money model, and the layouts we compared

The brief: monetise without drowning the user. Aspirants open this site because a
deadline is near, usually on a mid-range Android phone on mobile data. Every
decision below is sourced, not guessed.

---

## 1. How the money actually works

**AdSense pays an eCPM per impression. Clicks are optional.**

> "AdSense pays publishers an effective cost per mille (eCPM) for advertiser
> bids."
> — [AdSense revenue share](https://support.google.com/adsense/answer/180195)

> "For displaying ads with AdSense for Content, publishers receive 80% of the
> revenue, after the advertiser platform takes its fee… When advertisers use
> Google Ads to purchase display ads on AdSense, publishers keep about 68% of
> the revenue."
> — same page

So the answer to *"do they want clicks or just showing them?"* is: **showing them
is enough**. But the impression only counts if it is **viewable**.

**The viewability rule — this is the number that matters:**

> "We define a viewable impression as an ad that meets the following criteria:
> **50% of the ad's pixels need to be on screen for at least one continuous
> second.**"
> — [Viewability and Active View](https://support.google.com/adsense/answer/4510652)

> "A user must navigate to an area of the page where 50% of the ad's pixels are
> visible in the browser window. The user must pause or proceed slowly enough
> that the ad is on screen for one continuous second. **Scrolling past an ad
> too quickly won't count.**"
> — [Viewability best practices](https://support.google.com/adsense/answer/6219980)

> "**Short form content yields higher viewability, therefore set pages to have
> only one fold.**"
> — same page

> "Ad Placement: Place ads **in line with the main content or in content-rich
> areas** of the site."
> — same page

### What this means for us

| | |
| --- | --- |
| **Impressions pay, not clicks** | Never build a model that needs the click. |
| **Only viewable impressions pay** | An ad at the bottom of a long rail that nobody scrolls to is worth ~nothing. This is the single biggest mistake available to us. |
| **High CTR is a liability, not a goal** | "Encouraging accidental clicks" is a policy violation, and invalid traffic gets accounts terminated. Chasing clicks risks the whole revenue stream. |
| **Short pages win** | Google explicitly says one fold beats a long page. Our job list is long, so the rail has to be sticky for the ad to stay in view — otherwise the unit is dead weight. |

---

## 2. Where AdSense lets you put an ad — and where it doesn't

All quotes from [Ad placement policies](https://support.google.com/adsense/answer/1346295).

### Not allowed

- **Ads under a misleading heading.** *"Publishers may only label Google ads
  with either 'Advertisements' or 'Sponsored Links'."* The example given is a
  heading like "Resources" or "Helpful Links" — the ad gets mistaken for
  content. **This kills "an ad below Important Links".**
- **Content formatted to mimic ads** (and the reverse, ads disguised as
  content). *"Publishers may not implement Google ads in a manner that
  disguises the ads in any way."*
- **Encouraging accidental clicks** — ads that look like nav, menu, download or
  play buttons.
- **Unnatural attention to ads** — *"flashy animations that draw a user's eyes
  to the ads"*, *"arrows or other symbols pointing at the ads"*.
- **Auto-refresh, pre-roll, interstitials, pop-ups, pop-unders, new windows.**
- **Compensating users for clicks.**
- **Aligning images with ads** so users think the image belongs to the advertiser.

### Allowed

- **Anchor / sticky units.** Google's own anchor-ad format: *"Anchor ads stick
  to the edge of the user's screen and are easily dismissible"*, and *"When
  shown at the top, anchor ads only appear after the user has scrolled down far
  enough, so that they never cover your site's branding or navigation."*
  — [About anchor ads](https://support.google.com/adsense/answer/15484692)
- **In-content units**, as long as they are labelled and distinguishable.
- **Scripts that let the user close the unit.** What is *not* allowed is
  altering targeting: *"Adding irrelevant keywords… Using IFRAMEs with keywords
  to alter the content or language of the ads."*
  — [Special ad implementations](https://support.google.com/adsense/answer/1354742)

### The rule that shaped the layout

> An ad may never sit under a heading that implies what follows is content.

So the right rail is ordered **ad first, content after** — never the other way
round — and the sponsored cards in the feed carry their own label rather than
borrowing the "Latest Jobs" heading.

---

## 3. The four layouts we compared

The lab chrome (bottom-left) switches between them live, and the meter
(bottom-right) shows each slot's live viewability.

| Layout | Left rail | Right rail | Ads on screen at load | Measured viewability |
| --- | --- | --- | --- | --- |
| **A · Filter-first** | filters only | 1 ad, **above** content | 1 | 100% |
| **B · Rail-heavy** | filters only | 2 ads, **above** content | 2 | 100% / 100% |
| **C · Both rails** | **1 ad above filters** + filters | 1 ad above content | 2 | 100% / 100% |
| **D · Ads last** | filters only | 1 ad **below** content | 0 | **0%** |

Measured at 1440×900 on the live build.

**D is the trap.** It is the most "textbook-compliant" reading of the heading
rule and it is also the one that earns nothing — the unit sits at y=909 on a
900px-tall viewport, i.e. below the fold, so it records **0% visible** and
banks no viewable impressions until the user scrolls past the entire feed.

**C buys inventory with function.** The left rail is where ~69% of viewing time
happens (NN/G), so a left-hand ad is the best-viewed unit on the page — and it
also displaces the filters users came to use, and pushes the filter controls
below the fold.

---

## 4. Frequency cap

`AD_FREQUENCY = 8` — one sponsored card per eight organic notifications. The
cap is applied while the feed is assembled, not by the ad network, so it cannot
be exceeded by a fill or a retry.

**Still open:** the cap needs a server-side counterpart, or a user can defeat it
by paginating.

---

## 5. The sponsored card is a better product than an AdSense unit

The in-feed sponsored card is **not** a Google ad — it is a direct-sold listing
paid for by a recruiter. Two consequences:

1. **More money per impression.** No 32% platform cut, no 68% rev-share
   haircut. In a niche like Indian government exams there is a real, deep
   market — coaching institutes, test-prep SaaS, recruiters, banks doing campus
   hiring.
2. **Different rules.** AdSense's "special ad implementations" don't apply. What
   applies is the general principle: be unmistakable about what it is. Hence
   the dashed rule, the tinted paper, the muted type, the `SPONSORED` chip and
   the line *"Paid placement · not a government notification"* — and the
   deliberate absence of the `SARKARI` and `NEW` badges, so a sponsored card
   can never be mistaken for a government notification.

---

## 6. Recommendation

- **Right rail: one display unit, above the content panels** (layout A). It is
  in view on arrival, it is not under any heading, and it does not cost the
  user a control.
- **Left rail: filters only.** Any left-hand ad has to push the filters down.
- **Feed: sponsored job cards at 1 per 8.** Highest eCPM of anything we can
  run, because in-content inventory commands the best rates, and it is the
  format users are already trained to read.
- **Pro (₹99/mo) removes every ad** and adds the eligibility verdict on every
  card. The ad is the price of admission for the free tier.

---

## 7. Still open

- Real ad network integration (AdSense / programmatic) — the slot components are
  built so they can be swapped for a network tag.
- Server-side frequency capping.
- Viewability reporting wired to a real analytics property, so "is the left-rail
  ad actually being seen" is a number we check weekly, not a guess.
