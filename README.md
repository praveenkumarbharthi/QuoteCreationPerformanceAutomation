# Quote Creation Performance Automation

![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD-blue?logo=jenkins)
![JMeter](https://img.shields.io/badge/Apache%20JMeter-5.6.3-red?logo=apachejmeter)
![GitHub](https://img.shields.io/badge/GitHub-Source%20Control-black?logo=github)

An end-to-end **Performance Testing CI/CD pipeline** that automatically executes Apache JMeter load tests via Jenkins, generates an HTML dashboard report, and archives results as build artifacts.

---

## Project Overview

This project automates performance testing of the **Quote Creation API** flow using Apache JMeter integrated with Jenkins. On every build trigger, Jenkins checks out the latest test scripts from GitHub, executes the JMeter test in non-GUI mode, generates a full HTML performance dashboard, and archives results for historical comparison.

**APIs Under Test:**
- `POST /oauth/token` - Authentication
- `POST /quotes/v1/create` - Quote Creation
- `POST /v1/:quoteId/add-custom-items` - Add Custom Items to Quote

---

## Tech Stack

| Tool | Version | Purpose |
|------|---------|-------------------|
| Apache JMeter | 5.6.3 | Load & Performance Testing |
| Jenkins | 2.555.3 | CI/CD Automation |
| GitHub | - | Source Code Management |
| Groovy (Declarative Pipeline) | - | Jenkinsfile scripting |
| Windows Batch | - | JMeter execution script |

---

## Project Structure

```
QuoteCreationPerformanceAutomation/
├── jmeter/
│   ├── apache-jmeter-5.6.3/     # JMeter installation
│   └── createQuote.jmx          # JMeter test plan
├── scripts/
│   └── runJmeter.bat            # Windows batch execution script
├── properties/                   # JMeter properties overrides
├── testdata/                     # CSV test data files
├── results/                      # Generated: result.jtl, jmeter.log
├── reports/
│   └── html/                    # Generated: JMeter HTML dashboard
├── docs/                         # Documentation & screenshots
├── Jenkinsfile                   # Declarative Jenkins Pipeline
└── README.md
```

---

## Prerequisites

- Java 11 or higher
- Apache JMeter 5.6.3 (included in `jmeter/` folder)
- Jenkins 2.x with the following plugins:
  - HTML Publisher Plugin
  - Git Plugin
- Git

---

## How to Run Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/praveenkumarbharthi/QuoteCreationPerformanceAutomation.git
   ```

2. Run the test from the project root:
   ```bash
   scripts\runJmeter.bat
   ```

3. Open the HTML report:
   ```
   reports\html\index.html
   ```

---

## Jenkins Pipeline Flow

```
Checkout Source
     |
     v
Verify JMeter Installation
     |
     v
Run Performance Test
     |
     v
Validate Thresholds
     |
     v
Publish HTML Report + Archive Artifacts
```

### Jenkins Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| ENVIRONMENT | dev | Target environment (dev / qa / stage) |
| THREAD_COUNT | 10 | Number of concurrent virtual users |
| LOOP_COUNT | 5 | Iterations per thread |
| RAMP_UP | 10 | Ramp-up period in seconds |

### Performance Thresholds

| Metric | Threshold |
|--------|-----------|
| Error Rate | < 1% |
| Average Response Time | < 5000 ms |

---

## Sample Dashboard

The JMeter HTML Dashboard is published automatically after each Jenkins build.

Key sections available:
- **APDEX** - Application Performance Index per request
- **Requests Summary** - Pass/Fail pie chart
- **Statistics** - Samples, errors, avg/min/max/percentile response times, throughput
- **Over Time Charts** - Response time and throughput trends

---

## What This Project Demonstrates

- GitHub + Jenkins SCM integration
- Declarative Jenkins Pipeline (Jenkinsfile)
- Parameterized builds (environment, load profile)
- JMeter CLI non-GUI execution
- Automated HTML performance report publishing
- Build artifact archiving
- CI-based performance test execution with threshold validation

---

## Future Enhancements

- [ ] Email notification with HTML report after each build
- [ ] Jenkins Performance Plugin for cross-build trend graphs
- [ ] Nightly scheduled execution via Jenkins cron trigger
- [ ] Docker-based JMeter execution for portability
- [ ] Slack notification on build failure
- [ ] AWS EC2 distributed load injection

---

## Author

**Praveen Kumar Bharthi**  
Senior Quality Engineer | Performance Testing | DevOps  
[GitHub](https://github.com/praveenkumarbharthi)
