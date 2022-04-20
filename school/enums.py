from enumfields import Enum

class Role(Enum):
    STUDENT = 'student'
    TEACHER = 'teacher'
    PARENT = 'parent'
    STAFF = 'staff'
    ADMIN = 'admin'
    DEVELOPER = 'developer'

class Attendance_status(Enum):
    PRESENT = 'present'
    NOT_PRESENT = 'not-present'
    EXCUSED = 'excused'

class Booking_Status(Enum):
    REQUEST = 'request'
    ACCEPT = 'accept'
    REJECT = 'reject'
    
class Locations(Enum):
    TIANMU = 'tianmu'
    DAZHI = 'dazhi'
    DAAN = 'daan'
    TYPA = 'typa'
    TES = 'tes'
    HSINCHU = 'hsinchu'
    TREEHOUSE = 'treehouse'
    NONE = 'none'

class SessionType(Enum):
    CAMP = 'camp'
    CAMPFLEX = 'camp FLEX'
    CLUB = 'club'
    NONE = 'None'

class CampSessionType(Enum):
    AM = 'AM'
    PM = 'PM'
    PPM = 'PPM'
    FLEX = 'flex'
    FULL = 'full'
    NONE = 'None'

class Clubs(Enum):
    YOUNG_INVENTORS = 'Young Inventors'
    MACHINE_MAKERS = 'Machine Makers'
    CODE_WIZARDS = 'Code Wizards'
    TECH_JUMPSTART = 'Tech Jumpstart'
    PICO = "Pico"
    NANO = 'Nano'
    MILLI = 'Milli'
    MICRO = 'Micro'
    MEGA = 'Mega'
    GIGA = 'Giga'
    NONE = 'None'

class Days(Enum):
    MONDAY='monday'
    TUESDAY='tuesday'
    WEDNESDAY='wednesday'
    THURSDAY='thursday'
    FRIDAY='friday'
    SATURDAY='saturday'
    SUNDAY='sunday'

class PaymentStatus(Enum):
    CONFIRMED = 'confirmed'
    PENDING = 'pending'

class ClientStatus(Enum):
    ACTIVE = 'active'
    PENDING = 'pending'
    INACTIVE = 'inactive'

class StudentStatus(Enum):
    ACTIVE = 'active'
    PENDING = 'pending'
    INACTIVE = 'inactive'

class SessionStatus(Enum):
    ACTIVE = 'active'
    PENDING = 'pending'
    INACTIVE = 'inactive'

class BookingStatus(Enum):
    ACTIVE = 'active'
    PENDING = 'pending'
    INACTIVE = 'inactive'
    NONE = 'none'

class PaymentMethds(Enum):
    CASH = 'cash'
    BXB_CREDIT_CARD = 'bxb_credit_card'
    BXB_BANK_TRANSFER = "bxb_bank_transfer"
    CONSULTING_BANK_TRANSFER = "consulting_bank_transfer"
    DZ_POS_SYSTEM = 'dz_pos_system'
    CREDIT = 'credit'
    DEBIT = 'debit'
    OTHER = 'other'

class AttendanceStatus(Enum):
    ATTENDED = 'attended'
    NOSHOW = 'noshow'
    ABSENT = 'absent'
    ABSENT_WITH_CERT = 'absent with cert'
    NONE = 'none'