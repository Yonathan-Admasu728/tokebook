# Project Requirements & Role Permissions

## Role-Based Access Control

### Admin/Superuser

- **Casino Creation**: Exclusive ability to create new casino entries in the system
- Full system access and configuration capabilities

### Casino-Level User Roles

#### Dealer

- Can join/leave early-out list (own name only)
- Must sign off on tokes before shift start
- Can verify previous shift tokes
- Can submit discrepancy forms for incorrect toke amounts
- Cannot modify other users' early-out status
- Cannot post/update toke pool amounts

#### Supervisor

- Access to dedicated early-out management interface
- Can join/leave supervisors early-out list (own name only)

#### pencil

- Access to dedicated early-out management interface
- With "pencil"/"edit" flag:
  - Can authorize next person on early-out list
  - Can update early-out list status
- Cannot post toke pool amounts

#### Toke Manager

- Exclusive ability to post/update daily toke pool amounts
- Cannot modify early-out list without supervisor role
- can manage the dealers vacations
- can manage the daily toke list

## Core Functionality Requirements

### Casino Management

- Each casino maintains its own:
  - Employee roster
  - Role assignments
  - Early-out list
  - Toke management system

### Early-Out System

1. **Dealer Interface**
   - Join early-out list
   - Remove self from list
   - View current list status

2. **Supervisor Interface**
   - Join early-out list
   - Remove self from list
   - Authorize next person (with proper permissions) if the have access to pencil dashboard

### Toke Management

1. **Dealer Requirements**
   - Mandatory toke sign-off before shift start
   - Ability to verify previous shift toke amounts
   - Access to discrepancy reporting system

2. **Toke Manager Functions**
   - Post daily toke pool amounts
   - Update toke pool amounts as needed

### Discrepancy Handling

- Dealers can verify previous shift tokes
- Formal discrepancy reporting process
- Clear tracking of reported issues

## Security & Workflow Benefits

### Enhanced Security

- Role-based access control ensures proper authorization
- Segregated interfaces prevent unauthorized actions
- Comprehensive audit trail system tracking all user actions
- IP address tracking for security monitoring
- Detailed action logging with timestamps

### Streamlined Operations

- Separate dealer and supervisor interfaces
- Clear chain of command for early-out approvals
- Structured toke management process
- Real-time position tracking in early-out list
- Visual progress indicators for list position
- Shift information integration
- Wait time tracking

### Compliance & Accountability

- Tracked toke sign-offs
- Documented early-out authorizations
- Formal discrepancy reporting system
- Comprehensive reporting system including:

    Daily, weekly, and monthly summaries
    Custom period reports
    Dealer attendance tracking
    Peak hours analysis
    Toke distribution patterns
    Early-out request analytics
    Discrepancy resolution metrics

### Enhanced User Experience

- Position indicators in early-out list
- Visual progress bars
- Status badges with clear color coding
- Detailed shift information display
- Intuitive action buttons
- Real-time updates
- Mobile-responsive interfaces

### Advanced Reporting

- Flexible report generation
- Multiple report types (daily, weekly, monthly, custom)
- Key metrics visualization
- Trend analysis
- Performance indicators
- Compliance monitoring
- Resource utilization tracking

## Implementation Notes

### Frontend

- Separate routing for dealer and supervisor interfaces
- Role-based component rendering
- Permission-based action buttons

### Backend

- Role-based middleware/decorators
- Strict permission checking on all endpoints
- Audit logging for critical actions

### Database

- User-role relationships
- Casino-employee associations
- Audit trail capabilities
