# Stitch QA: 2-Minute Demo Video Walkthrough Script

**Project:** Stitch QA (AWS Agent Experience Hackathon: Strands Decider)  
**Author:** H7  
**Total Target Duration:** 120 seconds (2:00)  

---

## Act 1: The Problem (0:00 – 0:25)

**Visual:**
- Split-screen: A CI/CD pipeline failing on a minor network timeout vs a green pipeline passing with 0 tests executed.

**Voiceover:**
> "Continuous integration gates today are binary and blind. A passing pipeline might have zero tests written, while a transient network blip can halt production deployments. Engineering teams waste hours triaging whether a failure is a real defect or an environment fluke—and whether it's truly safe to release.
> 
> Meet **Stitch QA**—an autonomous pre-deployment release gate powered by Amazon Bedrock and Strands Decider 2B."

---

## Act 2: Multi-Model Architecture & Health Diagnostic (0:25 – 0:50)

**Visual:**
- Run diagnostic check:
  ```bash
  stitch check-bedrock
  ```
- Display the Rich CLI health diagnostic table showing Amazon Bedrock foundation models (Claude 3.5 Sonnet, Nova Lite, Nova Pro) and Strands Decider System 1 status.
- Highlight the architecture diagram from the README.

**Voiceover:**
> "Rather than using a single bloated model, Stitch QA tiers five specialized agents across Amazon Bedrock:
> - **Anthropic Claude 3.5 Sonnet v2** performs deep source AST quality review and surgical patch assurance.
> - **Amazon Nova Lite** ingests massive test logs for rapid, cost-effective root-cause triage.
> - **Amazon Nova Pro** formulates rigid repair contracts with protected blast boundaries.
> - And finally, **Strands Decider 2B** acts as the high-speed judicial gate, evaluating evidence vectors to issue discrete, confidence-calibrated release decisions in milliseconds."

---

## Act 3: Live Demo — Blocking a Runtime Defect (0:50 – 1:25)

**Visual:**
- Terminal recording running:
  ```bash
  stitch scan --run --analyze --repair --code-fix tests/fixtures/test-project
  ```
- Fast-forward through the Rich CLI output:
  - Source review completes.
  - Pytest detects `ZeroDivisionError`.
  - Runtime Analyst flags `APPLICATION_DEFECT`.
  - Repair contracts generated.
  - Strands Decider 2B prints:
    ```
    Strands Decider 2B System 1 Release Gate
    - Verdict: BLOCK_RELEASE
    - Confidence: 0.995
    - Choice Probabilities: BLOCK_RELEASE: 99.5%, ALLOW_RELEASE: 0.3%, QA_INCOMPLETE: 0.2%
    - Calibrated Risk: 0.95
    - Intervention Action: Deny
    - Decision Rationale: Blocking runtime defect confirmed. 1 repair contract(s) pending remediation.
    - Target Source: app.py
    ```
- Show CI exit code `1`.
- Briefly open `STITCH_QA_REPORT.md` in VS Code showing the structured repair guidance.

**Voiceover:**
> "Here, we scan a Python application with a defect. Stitch QA discovers the project structure, executes the test suite, and catches the ZeroDivisionError.
> 
> The Bedrock agents diagnose the application defect and produce bounded repair contracts. Then Strands Decider 2B steps in: issuing a definitive **BLOCK_RELEASE** verdict with 99% confidence and setting CI exit code 1 to halt the deployment."

---

## Act 4: Live Demo — Greenlighting Verified Code (1:25 – 1:45)

**Visual:**
- Terminal recording running:
  ```bash
  stitch scan --run tests/fixtures/test-docker-pytest-pass
  ```
- Output prints:
  ```
  Strands Decider 2B System 1 Release Gate
  - Verdict: ALLOW_RELEASE
  - Confidence: 0.983
  - Choice Probabilities: ALLOW_RELEASE: 98.3%, BLOCK_RELEASE: 1.2%, QA_INCOMPLETE: 0.5%
  - Calibrated Risk: 0.05
  - Intervention Action: Proceed
  ```
- Show CI exit code `0`.

**Voiceover:**
> "On a verified project, the full test suite passes. Strands Decider immediately outputs **ALLOW_RELEASE** with 97% confidence and exit code 0.
> 
> Notice how source-only projects without tests are flagged as **QA_INCOMPLETE**, ensuring untested code never slips through unverified."

---

## Act 5: Developer Experience & Wrap-up (1:45 – 2:00)

**Visual:**
- Show repository on GitHub, Docker container run, and the full test suite running and passing.

**Voiceover:**
> "Best of all, Stitch QA is offline-first. A built-in deterministic engine lets developers evaluate the full pipeline without entering credit cards or AWS keys upfront—elevating automatically to live Amazon Bedrock when credentials are configured.
> 
> Explore the open-source code and Docker container on GitHub at `hashan-7/stitch-qa-release-gate`. Ship faster, with absolute release certainty."

---

<div align="center">

**Developed with 💜 by H7**  
*AWS Agent Experience Hackathon: Strands Decider*

</div>
