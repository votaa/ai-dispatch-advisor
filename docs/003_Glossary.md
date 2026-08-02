# Glossary

## Purpose

This glossary defines common terms used across the AI Dispatch Advisor documentation and implementation. It is intended to reduce ambiguity across product, architecture, engineering, utility operations, security, and delivery discussions.

## Terms

### AI Dispatch Advisor

The enterprise software system being implemented in this repository. It provides AI-assisted outage dispatch recommendations, operational context, and explainability for electric utility outage management workflows.

### AIDA

An abbreviated name for AI Dispatch Advisor.

### Advanced Metering Infrastructure

Utility metering infrastructure that can provide meter events, outage indications, restoration indications, voltage information, and other customer-premise telemetry. Also referred to as AMI.

### AMI

See Advanced Metering Infrastructure.

### Assignment

A dispatch action or planned allocation of a crew to an outage, incident, work package, patrol, switching operation, or restoration task.

### Audit Event

A recorded event that captures system activity, recommendation generation, user review, user action, override reason, data context, or integration behavior for traceability.

### Circuit

An electrical distribution path that serves customers from a substation or feeder source. Circuit context can be important for outage grouping, switching constraints, and restoration planning.

### Crew

A field resource or work group available for outage response. Crew attributes may include location, skills, availability, shift status, equipment, certifications, and current assignment.

### Crew Suitability

The degree to which a crew is appropriate for a dispatch task based on capability, proximity, availability, equipment, safety requirements, and work type.

### Critical Facility

A facility whose outage may require priority attention due to public safety, health, infrastructure, or community impact. Examples may include hospitals, emergency services, water treatment facilities, shelters, and communication infrastructure.

### Customer Minutes Interrupted

A reliability measure representing the sum of customer outage duration across affected customers. Also referred to as CMI.

### CMI

See Customer Minutes Interrupted.

### Data Freshness

An indication of how current a data element or source is. Data freshness is important because dispatch recommendations may become less reliable when source data is stale.

### Decision Support

System behavior that assists human judgment without automatically executing operational decisions. The AI Dispatch Advisor is positioned as a decision-support system in its initial implementation phase.

### Dispatcher

An operations user responsible for evaluating outage events, assigning crews, coordinating response, and updating dispatch actions.

### Distribution Management System

An enterprise utility platform that supports monitoring and operation of the electric distribution network. Also referred to as DMS.

### DMS

See Distribution Management System.

### Estimated Time of Restoration

An estimate of when service will be restored for an outage event, customer group, or area. Also referred to as ETR.

### ETR

See Estimated Time of Restoration.

### Explainability

Structured information that helps a user understand why a recommendation was generated. Explainability may include contributing factors, constraints, assumptions, confidence indicators, source data, and expected impact.

### Feeder

A distribution line or circuit segment that carries power from a substation to downstream customers and equipment.

### Field Constraint

A real-world limitation that affects dispatch or restoration work. Examples include blocked access, flooding, hazardous conditions, crew certification requirements, switching dependencies, and equipment availability.

### Geographic Information System

The utility system of record for geospatial network, asset, landbase, and facility information. Also referred to as GIS.

### GIS

See Geographic Information System.

### Human-in-the-Loop

An operating model where the system provides recommendations and context, but a human user reviews and approves operational decisions.

### Incident

An outage event, trouble call, damage report, hazard report, or related operational event requiring evaluation or response. Some utilities may distinguish incidents from outages based on source system terminology.

### Integration Adapter

A software component that isolates vendor-specific protocols, schemas, authentication mechanisms, and data mapping logic from the rest of the application.

### Mutual Assistance

Support provided by external utility crews or contractors during major outage events, usually coordinated through formal mutual assistance agreements.

### Network Topology

The modeled connectivity of electric distribution assets, circuits, switches, protective devices, transformers, and service points.

### Outage

An interruption of electric service affecting one or more customers, assets, feeders, circuits, or service areas.

### Outage Management System

The utility platform that manages outage events, outage prediction, restoration status, crew assignment, customer impact, and related operational workflows. Also referred to as OMS.

### OMS

See Outage Management System.

### Override

A user action that rejects or modifies a system recommendation. Overrides should be expected, supported, and captured for audit and learning.

### Recommendation

A system-generated dispatch suggestion. A recommendation may propose an outage priority, crew assignment, restoration sequence, scenario, or operational action.

### Recommendation Confidence

An indication of how strongly the system supports a recommendation based on available data, model logic, constraints, and uncertainty. Confidence should not be presented as a guarantee.

### Restoration Sequence

The planned order in which outage work, switching steps, patrols, repairs, or crew assignments should occur to restore service.

### SCADA

Supervisory Control and Data Acquisition. A utility operational system that provides telemetry, equipment status, alarms, and control-related data for grid operations.

### Scenario

A dispatch or restoration option that can be compared against alternatives. Scenarios may differ by crew assignment, priority order, restoration sequence, or operating assumptions.

### Supervisory Control and Data Acquisition

See SCADA.

### Storm Mode

An operational mode used during major weather or outage events when outage volume, crew coordination, prioritization, and reporting needs differ from routine operations.

### System of Record

The authoritative enterprise system for a particular data domain or operational action. The AI Dispatch Advisor is not intended to replace systems of record in the initial implementation.

### Work Package

A collection of tasks, incidents, repairs, inspections, or switching steps that can be assigned to a crew as a coherent unit of work.

## Maintenance

Terms should be added or revised when new domain concepts, system components, user roles, data entities, or integration terms appear in documentation or implementation.

