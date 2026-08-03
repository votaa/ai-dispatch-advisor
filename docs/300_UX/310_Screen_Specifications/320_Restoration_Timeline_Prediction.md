# Restoration Timeline and Prediction Screen Specification

## Purpose

Provide real-time restoration progress, AI-powered restoration forecasts, milestone tracking, confidence bands, and key operational factors that influence estimated restoration timelines.

## Screen Visual

![Restoration Timeline and Prediction screen visual](<../../assets/screenshots/Restoration Timeline Analytics Dashboard.png>)

Screenshot status: Approved mockup PNG provided by project owner.

## Primary User

Dispatch Supervisor, Storm Response Coordinator, Operations Analyst

## Layout Specification

- Restoration metric summary
- Restoration timeline chart
- Forecast milestones
- Restoration phases
- AI forecast insights
- Confidence bands and data sources

## Key UI Components

- Customers out
- Estimated 90% restoration
- Restoration progress
- Estimated 100% restoration
- Restoration rate
- Milestones and key events
- Factors influencing forecast

## User Actions

- Review projected restoration milestones
- Recalculate ETRs
- Run what-if scenario
- Update forecast
- Export timeline
- Inspect data quality

## Data Requirements

- Active incident history
- Restoration progress events
- OMS status updates
- SCADA status
- Crew tracking
- Weather forecast
- GIS/network context

## Backend and API Dependencies

- `Future: GET /api/restoration/timeline`
- `Future: GET /api/restoration/forecast`
- `Future: POST /api/restoration/recalculate`

## AI and Recommendation Behavior

AI forecasting should estimate restoration milestones, identify operational factors influencing ETRs, expose confidence bands, and keep forecasts advisory until validated by operations users.

## Audit Requirements

Forecast updates, ETR recalculations, and exported timeline reports should be auditable when used for operational decision-making or stakeholder communication.

## Accessibility Notes

- Preserve keyboard access for all interactive controls.
- Do not rely on color alone for severity, status, confidence, or integration health.
- Keep dense operational data readable at expected dispatcher workstation sizes.
- Provide visible focus and confirmation states for user actions.

## Acceptance Criteria

- Restoration progress and forecast milestones are visible
- Forecast confidence and data sources are visible
- Users can identify factors influencing forecast accuracy
- Timeline can support storm response coordination

## Related Documents

- [UI Information Architecture](../301_UI_Information_Architecture.md)
- [Dispatch Console Specification](../302_Dispatch_Console_Specification.md)
- [Recommendation Experience](../303_Recommendation_Experience.md)
- [Explainability and Trust](../304_Explainability_and_Trust.md)
