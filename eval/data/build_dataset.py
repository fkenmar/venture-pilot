"""Builds transcripts.jsonl — the Phase 0.1 seed eval set.

These transcripts are *realistically simulated* (per ROADMAP 0.1) and engineered to
test ONE thing: can a model separate genuine buying signal from politeness?

Design (grounded in The Mom Test + First Round's signal-vs-politeness framing):
  - 6 CONTINUE: genuine signal — current quantified pain, money/time committed,
    specific past behavior, urgency, asks price / offers to pay / makes intros.
  - 6 STOP: no real signal — compliments, hypotheticals, no current pain, no budget.
  - 6 PIVOT: real, paid pain that points at a DIFFERENT problem/segment than pitched.

Trap design (the discriminating records — a sentiment-follower gets these WRONG):
  - false_positive : effusively positive tone, zero substance  -> truth = STOP
  - false_negative : skeptical/negative tone, strong substance  -> truth = CONTINUE
  - every PIVOT     : engaged & positive, but about the wrong thing -> truth = PIVOT

Each record also carries `naive_sentiment_guess`: the verdict a reader who follows
TONE rather than substance would give. The eval's headline test is whether the model
beats this naive baseline on the discriminator subset.

The judge (verdict.py) only ever sees: id, idea, segment, transcript.
Everything else here is held-out ground truth.

Replace/augment with REAL transcripts as they are collected (Phase 0.2 sessions).
"""

import json
import os

RECORDS = [
    # ---------------------------------------------------------------- CONTINUE
    {
        "id": "t01",
        "idea": "A tool that auto-texts/calls patients to cut dental-clinic no-shows.",
        "segment": "Dental clinic office managers",
        "transcript": (
            "Founder: How do you handle no-shows today?\n"
            "Manager: It's our biggest headache. Last month we had 47 no-shows — that's maybe $9,000 in lost chair time.\n"
            "Founder: What do you do about it now?\n"
            "Manager: Two front-desk staff spend the first hour every morning calling tomorrow's patients. I'm paying overtime for it. We tried a generic reminder text but it wouldn't let patients reschedule, so they ignored it.\n"
            "Founder: If a tool handled the outreach and let them reschedule in one tap?\n"
            "Manager: How much? We pay a reminder service $140 a month and it's useless. If yours actually cut no-shows I'd switch tomorrow. Can we pilot next month? I can also get you in front of the two other clinics our owner runs."
        ),
        "ground_truth": "CONTINUE",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["quantified pain ($9k / 47)", "current paid workaround (overtime + $140 service)", "explicit switch intent + timeline", "offers warm intros"],
        "rationale": "Quantified current pain, existing spend, concrete commitment and timeline, and intros — strong genuine demand.",
    },
    {
        "id": "t02",
        "idea": "Software that automatically chases late freelance invoices.",
        "segment": "Solo freelancers / consultants",
        "transcript": (
            "Founder: Would a tool that chases your late invoices be useful?\n"
            "Freelancer: Honestly? I'm skeptical. I've tried like four productivity things and they're all junk. I don't think software fixes people who don't pay.\n"
            "Founder: How do you handle late payments today?\n"
            "Freelancer: Ugh. Three spreadsheets and a Notion board. Last year I straight-up lost about $4,000 because I forgot to follow up on two invoices and it got awkward. I send reminders myself, when I remember — which is the problem.\n"
            "Founder: What would it need to do for you to use it?\n"
            "Freelancer: If it pulled from my invoicing tool and sent escalating reminders without me thinking about it, and let me sound polite not aggressive, I'd pay for that today. What's the price? I'm not optimistic but I'd genuinely try it this week."
        ),
        "ground_truth": "CONTINUE",
        "trap_type": "false_negative",
        "naive_sentiment_guess": "STOP",
        "discriminating_signals": ["skeptical TONE", "but: quantified loss ($4k)", "current workaround (3 spreadsheets)", "conditional commitment + 'pay today' + 'this week' + asks price"],
        "rationale": "Negative tone masks strong substance: real quantified pain, active workaround, and concrete willingness to pay now. A tone-follower wrongly says STOP.",
    },
    {
        "id": "t03",
        "idea": "An app that tracks restaurant inventory and flags spoilage risk.",
        "segment": "Independent restaurant owners",
        "transcript": (
            "Owner: Spoilage is killing me — easily $2,000 a month in produce I throw out.\n"
            "Founder: How do you track inventory now?\n"
            "Owner: I built a monster Google Sheet, and my sous chef counts by hand on Sundays. It's always wrong by Wednesday. I looked at the big POS inventory add-ons but they're $400 a month and built for chains.\n"
            "Founder: If something flagged what to use first and reordered smartly?\n"
            "Owner: That's exactly the problem. Send me the contract — I'll do a paid trial across both my locations. When can you start?"
        ),
        "ground_truth": "CONTINUE",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["$2k/mo pain", "current workaround", "evaluated priced alternatives", "'send the contract' + paid trial + urgency"],
        "rationale": "Clear pain, rejected alternatives for concrete reasons, asks for the contract — strong.",
    },
    {
        "id": "t04",
        "idea": "A tool that turns long podcast episodes into short social clips automatically.",
        "segment": "Independent podcasters",
        "transcript": (
            "Podcaster: Clips are where the growth is, but I hate making them.\n"
            "Founder: What do you do now?\n"
            "Podcaster: I pay an editor $600 a month for about 8 clips, and I also pay for two AI tools that half-work — so I'm double-paying. It still takes me hours picking moments.\n"
            "Founder: If one tool picked the best moments and cut them to spec?\n"
            "Podcaster: I'd drop the editor and one tool immediately. I'm already spending the money — I just want it to work. What's your pricing? Put me on the beta, here's my card if you need it."
        ),
        "ground_truth": "CONTINUE",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["current spend ($600 + 2 tools)", "explicit switch intent", "asks pricing + offers card"],
        "rationale": "Already paying for the job-to-be-done; concrete switch intent and payment willingness.",
    },
    {
        "id": "t05",
        "idea": "Scheduling software for community-college tutoring centers.",
        "segment": "College tutoring-center directors",
        "transcript": (
            "Director: Scheduling tutors against student demand is a nightmare every semester.\n"
            "Founder: How is it handled now?\n"
            "Director: A part-time coordinator and a shared Google Calendar. We overbook some slots and leave others empty. I actually have a software budget line for this — about $5k a year — that I haven't spent because nothing fits higher-ed.\n"
            "Founder: If it matched demand to availability and reported utilization for your funding reports?\n"
            "Director: The utilization reporting is huge for our grant renewals. We have an RFP cycle in the fall. Can you demo for my dean next month?"
        ),
        "ground_truth": "CONTINUE",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["existing unspent budget line ($5k)", "current workaround", "specific need (grant reporting)", "buying process (RFP) + demo request"],
        "rationale": "Budget exists, real workflow pain, concrete buying process and next step.",
    },
    {
        "id": "t06",
        "idea": "A booking and deposit-payment app for independent pet sitters.",
        "segment": "Self-employed pet sitters",
        "transcript": (
            "Sitter: I lose bookings constantly because I'm slow to text people back while I'm with animals.\n"
            "Founder: How do you book and get paid now?\n"
            "Sitter: Texts and Venmo. I lost a few hundred dollars last month to people who booked someone faster, and two clients 'forgot' to pay. I tried Wag and Rover but they take a huge cut and own my clients.\n"
            "Founder: If you had your own booking page with deposits taken upfront?\n"
            "Sitter: Deposits upfront would fix the no-pay thing. I'd pay a monthly fee to keep my own clients. Can I get in early? I'll pre-pay the first few months to lock it in."
        ),
        "ground_truth": "CONTINUE",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["lost revenue quantified", "current workaround", "rejected alternatives for real reason", "offers to pre-pay"],
        "rationale": "Concrete lost revenue, clear reason incumbents fail, prepay offer.",
    },
    # -------------------------------------------------------------------- STOP
    {
        "id": "t07",
        "idea": "An AI journaling app that gives you daily reflection prompts.",
        "segment": "Young professionals interested in wellness",
        "transcript": (
            "Prospect: Oh my gosh, I LOVE this. This is genius. Everyone I know needs this.\n"
            "Founder: Do you journal now?\n"
            "Prospect: Not really, I keep meaning to. But this would totally get me to start!\n"
            "Founder: When did you last try?\n"
            "Prospect: I downloaded one a while ago, used it twice. But yours sounds way better!\n"
            "Founder: Would you pay for it?\n"
            "Prospect: Maybe? Depends. But honestly this is such a great idea, you should 100% build it. I'd definitely use it when it's out."
        ),
        "ground_truth": "STOP",
        "trap_type": "false_positive",
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["effusive praise", "no current behavior", "abandoned a similar app", "no commitment, hypothetical future tense"],
        "rationale": "Maximum enthusiasm, zero substance: no current pain, churned on a competitor, no commitment. Classic compliment trap.",
    },
    {
        "id": "t08",
        "idea": "A social app that matches people for spontaneous weekend plans.",
        "segment": "Urban 20-somethings (interviewed a friend)",
        "transcript": (
            "Friend: Dude, this is awesome. You should build this, it's a great idea.\n"
            "Founder: Do you struggle to make weekend plans now?\n"
            "Friend: Eh, not really, I just text my group chat. But for other people this would be huge!\n"
            "Founder: Would you use it?\n"
            "Friend: For sure, I'd download it to support you! Maybe not every weekend, but yeah. You've got this, man — it's gonna blow up."
        ),
        "ground_truth": "STOP",
        "trap_type": "false_positive",
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["supportive friend", "no personal pain (group chat works)", "'support you' = compliment not demand", "deflects to 'other people'"],
        "rationale": "Friend politeness; admits no personal problem; demand projected onto hypothetical others.",
    },
    {
        "id": "t09",
        "idea": "An enterprise dashboard that consolidates DevOps alerts.",
        "segment": "Engineers at mid-size tech companies",
        "transcript": (
            "Engineer: Yeah, interesting. We get a lot of alerts.\n"
            "Founder: Is alert overload a problem for your team?\n"
            "Engineer: Our SRE team owns that. I personally don't deal with it much. We use PagerDuty and it's fine, I think.\n"
            "Founder: Would consolidating across tools help?\n"
            "Engineer: Maybe? You'd have to ask our platform lead, that's not my call. Seems useful in general. Send me a link, I'll pass it along if I remember."
        ),
        "ground_truth": "STOP",
        "trap_type": None,
        "naive_sentiment_guess": "STOP",
        "discriminating_signals": ["no authority/ownership", "no personal pain", "incumbent 'fine'", "'if I remember' deferral"],
        "rationale": "Wrong contact, no pain, satisfied with incumbent, weak deferral. No signal.",
    },
    {
        "id": "t10",
        "idea": "A fitness app that gamifies workouts with streaks and rewards.",
        "segment": "People who want to get in shape",
        "transcript": (
            "Prospect: This sounds amazing! I love streaks, that would totally motivate me.\n"
            "Founder: How do you work out now?\n"
            "Prospect: I don't, really — that's the thing. I keep starting and stopping.\n"
            "Founder: Used fitness apps before?\n"
            "Prospect: Oh yeah, like five. I always quit after two weeks. But yours sounds more fun!\n"
            "Founder: Would you pay a subscription?\n"
            "Prospect: Maybe a small one? Honestly I'd probably use the free version. But I really think you're onto something — this could be big!"
        ),
        "ground_truth": "STOP",
        "trap_type": "false_positive",
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["enthusiasm", "serial abandoner (5 apps, quits in 2 wks)", "free-rider intent", "hypothetical"],
        "rationale": "Excited but self-reports the exact churn behavior that kills the product; wants the free tier.",
    },
    {
        "id": "t11",
        "idea": "A tool that auto-summarizes internal team meetings.",
        "segment": "Operations managers at SMBs",
        "transcript": (
            "Manager: Sure, summaries are nice I guess.\n"
            "Founder: Is capturing meeting notes a pain for your team?\n"
            "Manager: Not really. Whoever runs the meeting jots action items in our shared doc and emails them. Works fine for us.\n"
            "Founder: Ever miss things or get confused later?\n"
            "Manager: Occasionally, but not enough that I'd buy something. We're disciplined with the doc. It's not a burning issue."
        ),
        "ground_truth": "STOP",
        "trap_type": None,
        "naive_sentiment_guess": "STOP",
        "discriminating_signals": ["explicitly not a pain", "working solution", "'not burning'", "no intent"],
        "rationale": "Directly states it isn't a problem worth paying for. Honest no-signal.",
    },
    {
        "id": "t12",
        "idea": "A marketplace for handmade greeting cards.",
        "segment": "Interviewed a supportive family member",
        "transcript": (
            "Respondent: Oh sweetheart, this is wonderful. You're so talented — I think it's a lovely idea.\n"
            "Founder: Do you buy handmade cards online now?\n"
            "Respondent: Well, I usually grab one at the store. But yours would be so much nicer!\n"
            "Founder: Would you shop on the marketplace?\n"
            "Respondent: Of course, dear, I'd buy from you any day. Whatever you make, I'll support it. It's going to be wonderful."
        ),
        "ground_truth": "STOP",
        "trap_type": "false_positive",
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["affection/compliments", "current behavior (store) unchanged", "'support you' not market demand"],
        "rationale": "Pure familial encouragement; no behavior change, no market signal.",
    },
    # ------------------------------------------------------------------- PIVOT
    {
        "id": "t13",
        "idea": "An AI meal-planning app for busy parents.",
        "segment": "Working parents who cook",
        "transcript": (
            "Parent: Meal planning? Eh, I kind of wing it — that's not really my issue.\n"
            "Founder: What is the hard part of feeding your family?\n"
            "Parent: Honestly it's grocery delivery. Half my Instacart order comes with random substitutions — they swap the thing I needed and the recipe falls apart, or it's wasted. I throw out maybe $50 of wrong items a week.\n"
            "Founder: So the planning isn't the pain, the shopping execution is?\n"
            "Parent: Exactly. If something caught bad substitutions before they shipped and suggested fixes, I'd pay for that in a heartbeat. The planning I'm fine with."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["pitched idea (planning) = no pain", "strong pain + WTP on adjacent problem (substitutions/waste)"],
        "rationale": "Engaged and willing to pay — but for a different problem than pitched. Signal says pivot, not continue.",
    },
    {
        "id": "t14",
        "idea": "Time-tracking software for creative agencies.",
        "segment": "Agency owners",
        "transcript": (
            "Owner: Time tracking? We use Harvest, it's fine — not a problem for us.\n"
            "Founder: So tracking hours isn't painful?\n"
            "Owner: No. What's killing us is collections. We bill the hours fine, but clients pay 60, 90 days late and chasing them is a part-time job. We're floating payroll on a credit line because of it.\n"
            "Founder: If the tool got invoices paid faster instead of tracking time?\n"
            "Owner: Now THAT I'd buy today. Time tracking is solved. Late payment is an existential thing for us."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["pitched thing solved by incumbent", "strong pain + 'buy today' on adjacent (collections)"],
        "rationale": "Strong WTP, but explicitly for collections, not time tracking. Pivot the wedge.",
    },
    {
        "id": "t15",
        "idea": "A consumer app for learning travel phrases in any language.",
        "segment": "Frequent travelers",
        "transcript": (
            "Prospect: Travel phrases? I just use Google Translate when I travel, it's good enough.\n"
            "Founder: So you wouldn't pay for a travel-focused one?\n"
            "Prospect: Probably not for travel. But — I'm a nurse. At work I constantly need medical phrases for patients who don't speak English, and Google Translate is risky for medical stuff. There's nothing good and HIPAA-safe for that. My unit would absolutely pay for something accurate.\n"
            "Founder: So the real demand is medical interpreting, not travel?\n"
            "Prospect: For me, yes. The travel thing, meh. The hospital thing — I'd push my manager to buy it."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["consumer/travel use = no demand (incumbent good enough)", "strong B2B/medical demand: different segment, buyer, WTP"],
        "rationale": "Real, fundable demand exists — in a different segment and use case. Pivot both problem and buyer.",
    },
    {
        "id": "t16",
        "idea": "A CRM built for real-estate agents.",
        "segment": "Real-estate team leads",
        "transcript": (
            "Lead: Another realtor CRM? We have like three. They're all the same — commodity.\n"
            "Founder: So a better CRM wouldn't move you?\n"
            "Lead: No. The thing nobody solves is lead routing across my team. When a lead comes in — who gets it, how fast, what if they sit on it? We lose deals to slow response and I can't see it happening. I'd pay real money to fix that.\n"
            "Founder: So lead routing and accountability, not the CRM itself?\n"
            "Lead: Right. The CRM is table stakes. Routing is where the money leaks."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["pitched (CRM) commoditized, no demand", "strong WTP on adjacent feature (lead routing)"],
        "rationale": "Clear money on the table — for routing, not the CRM. Pivot the feature focus.",
    },
    {
        "id": "t17",
        "idea": "A social app for sharing and discovering home recipes.",
        "segment": "Home cooking enthusiasts",
        "transcript": (
            "Cook: Sharing recipes? I just post on Instagram — that's free and fine.\n"
            "Founder: So a dedicated app doesn't pull you?\n"
            "Cook: Not for the social part. But I run a small catering side business, and scaling a recipe from 4 to 80 people and costing the ingredients is a brutal manual mess in spreadsheets. I'd pay for something that did recipe scaling and food-cost math.\n"
            "Founder: So the value is the catering/costing side, not social sharing?\n"
            "Cook: Yes. The social thing is a hobby. The catering math is money I'd happily spend to save."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "CONTINUE",
        "discriminating_signals": ["B2C social = no demand", "strong B2B costing pain + WTP"],
        "rationale": "Demand is real but B2B (catering costing), not the B2C social pitch. Pivot.",
    },
    {
        "id": "t18",
        "idea": "A 'Notion for law firms' all-in-one workspace.",
        "segment": "Small-law-firm office administrators",
        "transcript": (
            "Admin: The features look nice, but honestly we already have a case-management system we tolerate.\n"
            "Founder: Would the workspace features pull you to switch?\n"
            "Admin: Not the features themselves. The reason we're stuck is our data — fifteen years of case files trapped in an ancient system that nobody can migrate without losing the structure. That's why we never switch tools.\n"
            "Founder: So the blocker is migration, not the workspace?\n"
            "Admin: Exactly. If you could get our data out cleanly, we'd consider anything. The shiny workspace isn't the point — the migration is. We'd pay just for that."
        ),
        "ground_truth": "PIVOT",
        "trap_type": None,
        "naive_sentiment_guess": "STOP",
        "discriminating_signals": ["lukewarm/negative tone", "pitched value (features) doesn't move them", "real pain + WTP is data migration"],
        "rationale": "Tone reads negative and the pitched product is rejected — but a fundable adjacent pain (migration) is named with WTP. Pivot, not stop.",
    },
]

JUDGE_VISIBLE_FIELDS = ("id", "idea", "segment", "transcript")
LABELS = ("STOP", "PIVOT", "CONTINUE")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "transcripts.jsonl")
    # integrity checks before writing
    seen = set()
    for r in RECORDS:
        assert r["id"] not in seen, f"duplicate id {r['id']}"
        seen.add(r["id"])
        assert r["ground_truth"] in LABELS, r["id"]
        assert r["naive_sentiment_guess"] in LABELS, r["id"]
        assert r["trap_type"] in (None, "false_positive", "false_negative"), r["id"]
    with open(out, "w") as f:
        for r in RECORDS:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = {l: sum(1 for r in RECORDS if r["ground_truth"] == l) for l in LABELS}
    traps = sum(1 for r in RECORDS if r["trap_type"])
    print(f"wrote {len(RECORDS)} records -> {out}")
    print(f"class balance: {counts} | trap records: {traps}")


if __name__ == "__main__":
    main()
