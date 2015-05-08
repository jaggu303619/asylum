from openerp.osv import fields, osv

class hotel_book_order(osv.Model):
    _name = "hotel.book.order"
    _description = "Hotel Book Order"
    _columns = {
        'guest_ref': fields.char('Guest Ref.', size=128, required=True,),
        'first_name': fields.char('First Name', size=128, required=True, ),
        'last_name': fields.char('Last Name', size=128, required=True,),
        'gender': fields.selection([('m', 'Male'), ('f', 'Female')], 'Gender', ),
        'guest_type': fields.many2one('hotel.guest.type', 'Guest Type',),
        'country_id': fields.many2one('res.country', 'Country',),
        'room_id': fields.many2one('hotel.room', 'Room Number', required=True, ondelete='cascade',),
        # 'room_id_view':fields.function(_get_auto_room_id_view, string='Room Number', type='char',store=True),
        'check_in_date': fields.datetime('Check - In', help="Check-in Time.", required=True,),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
    }