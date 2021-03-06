from openerp.osv import fields, osv
import time
from datetime import datetime
from datetime import timedelta
from openerp.tools.translate import _
import base64


class tarun_hotel_purchase(osv.osv):
    _name = "tarun.hotel.purchase"
    _description = "Purchase Order"

    def order_lines_change(self, cr, uid, ids, lines, partner_id=False, context=None):
        context = context or {}
        prod_obj = self.pool.get('tarun.hotel.product')
        guest_obj = self.pool.get('tarun.hotel.guest.partner')
        line_obj = self.pool.get('tarun.hotel.purchase.lines')
        tot = 0.0
        bal = 0.0
        if not ids:
            if lines:
                for line in lines:
                    if line[2]['product_id']:
                        val = prod_obj.read(cr, uid, line[2]['product_id'], ['value'])[
                            'value'] * line[2]['qty']
                        tot += val
        else:
            for l in lines:
                if l[1]:
                    for x in line_obj.browse(cr, uid, [l[1]]):
                        tot += x.pts
                else:
                    if l[2]['product_id']:
                        val = prod_obj.read(cr, uid, l[2]['product_id'], ['value'])[
                            'value'] * l[2]['qty']
                        tot += val
        if partner_id:
            pbal = guest_obj.read(cr, uid, partner_id, ['points'])['points']
        else:
            pbal = 0.0

        bal = pbal - tot
        return {'value': {'total': tot, 'balance': bal}}

    def _get_total(self, cr, uid, ids, field_name, arg, context=None):
        """
        @return: Dictionary of values.
        """
        ords = self.browse(cr, uid, ids, context=context)
        res = {}
        for ord in ords:
            val = 0.0
            if ord.inv_lines:
                for lines in ord.inv_lines:
                    val += lines.pts
            res[ord.id] = val
        return res

    def _get_balance(self, cr, uid, ids, field_name, arg, context=None):
        """
        @return: Dictionary of values.
        """
        ords = self.browse(cr, uid, ids, context=context)
        res = {}
        for ord in ords:
            val = 0.0
            if ord.guest_id:
                bal = ord.guest_id.points
            else:
                bal = 0.0
            if ord.inv_lines:
                for lines in ord.inv_lines:
                    val += lines.pts
            res[ord.id] = bal - val
        return res

    def button_update(self, cr, uid, ids, context=None):
        return True

    def button_cancel(self, cr, uid, ids, context=None):

        for do in self.browse(cr, uid, ids, context=context):
            time_now = time.strftime('%Y-%m-%d %H:%M:%S')
            return self.write(cr, uid, ids, {'state': 'cancel', 'date': time_now, }, context=context)

    def button_done_bill(self, cr, uid, ids, context=None):
        for do in self.browse(cr, uid, ids, context=context):
            time_now = time.strftime('%Y-%m-%d %H:%M:%S')
            try:
                stock = self.pool.get('tarun.hotel.stock.location').search(
                    cr, uid, [('name', 'ilike', 'stock')])
                sale = self.pool.get('tarun.hotel.stock.location').search(
                    cr, uid, [('name', 'ilike', 'sale')])
            except:
                raise osv.except_osv(_('Location Error!'), _(
                    'Please create location name "Stock" and "Sale"! Contact Administrator'))
            if do.balance < 0.0:
                raise osv.except_osv(
                    _('Warning!'), _('Guest doesnot have enough points to process the order.!'))
            for lines in do.inv_lines:
                self.pool.get('tarun.hotel.stock.transfer').create(cr, uid, {'name': do.name,
                                                                             'product_id': lines.product_id.id,
                                                                             'qty': lines.qty,
                                                                             'loc_id': stock[0],
                                                                             'loc_des_id': sale[0],
                                                                             'date': time_now,
                                                                             'user_id': uid,
                                                                             'state': 'done'}, context=context)
            self.pool.get('tarun.hotel.guest.points').create(cr, uid, {'guest_id': do.guest_id.id,
                                                                       'name': do.name,
                                                                       'purchase_id': do.id,
                                                                       'qty': -do.total,
                                                                       'date': time_now,
                                                                       }, context=context)
            self.write(
                cr, uid, ids, {'state': 'done', 'date': time_now, }, context=context)
            return {
                'type': 'ir.actions.report.xml',
                        'report_name': 'tarun.hotel.purchase',
                        'datas': {
                            'model': 'tarun.hotel.purchase',
                            'id': ids and ids[0] or False,
                            'ids': ids and ids or [],
                            'report_type': 'pdf'
                        },
                'nodestroy': True
            }

    def button_go_bill(self, cr, uid, ids, context=None):
        for do in self.browse(cr, uid, ids, context=context):
            tot = sum([l.pts for l in do.inv_lines])
            pbal = do.guest_id.points
            time_now = time.strftime('%Y-%m-%d %H:%M:%S')
            return self.write(cr, uid, ids, {'state': 'bill', 'date': time_now, 'total_final': tot, 'total': tot, 'balance_final': do.guest_id.points - tot, 'balance': do.guest_id.points - tot, }, context=context)

    def button_back_bill(self, cr, uid, ids, context=None):
        for do in self.browse(cr, uid, ids, context=context):
            return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    _columns = {
        'guest_id': fields.many2one('tarun.hotel.guest.partner', 'Guest Billing', select=True),
        'name': fields.char('Name', size=128, required=True, select=True),
        'total': fields.function(_get_total, string='Total', type='float'),
        #'balance': fields.function(_get_balance, string='Balance', type='float'),
        'total_final': fields.float('Total'),
        'balance_final': fields.float('Balance'),
        'balance': fields.float('Balance'),
        'date': fields.datetime('Date', help="Date.", required=True, select=True, readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('bill', 'Billed'),
            ('done', 'Done'),
            ('cancel', 'Cancel'),
        ], 'Status', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'inv_lines': fields.one2many('tarun.hotel.purchase.lines', 'inv_id', 'Purchase Order Lines', readonly=True, states={'draft': [('readonly', False)]}),
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: '/',
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').get(
                cr, uid, 'tarun.hotel.purchase') or '/'

        return super(tarun_hotel_purchase, self).create(cr, uid, vals, context=context)


tarun_hotel_purchase()


class tarun_hotel_purchase_lines(osv.osv):
    _name = "tarun.hotel.purchase.lines"
    _description = "Purchase Order Lines"

    def _get_total_pts(self, cr, uid, ids, field_name, arg, context=None):
        """
        @return: Dictionary of values.
        """
        lines = self.browse(cr, uid, ids, context=context)
        res = {}
        for line in lines:
            res[line.id] = line.product_id.value * line.qty
        return res

    def _get_pts_unit(self, cr, uid, ids, field_name, arg, context=None):
        """
        @return: Dictionary of values.
        """
        lines = self.browse(cr, uid, ids, context=context)
        res = {}
        for line in lines:
            res[line.id] = line.product_id.value
        return res

    _columns = {
        'inv_id': fields.many2one('tarun.hotel.purchase', 'INV'),
        'product_id': fields.many2one('tarun.hotel.product', 'Product', required=True, select=True),
        'pts_unit': fields.float('Points', digits=(14, 3)),
        'pts': fields.function(_get_total_pts, string='Total Points', type='float', readonly=True),
        'qty': fields.float('Quantity', digits=(14, 3)),
    }

    def create(self, cr, uid, vals, context=None):
        if not vals['product_id']:
            return True
        if not vals.get('pts_unit', None):
            vals['pts_unit'] = self.pool.get('tarun.hotel.product').read(
                cr, uid, vals['product_id'], ['value'])['value']
        return super(tarun_hotel_purchase_lines, self).create(cr, uid, vals, context=context)

    def product_id_change(self, cr, uid, ids, product, partner_id=False, flag=False, context=None):
        context = context or {}
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _(
                'Please use Cashier Page,\n to initiate the order.'))
        return {'value': {'qty': 1.00, 'product_id': product}}

    def onchange_product_id(self, cr, uid, ids, product_id, qty, context=None):
        """ Otherwise a warning is thrown.            
        """
        res = {'value': {}}
        if not product_id:
            return res
        else:
            for prod in self.pool.get('tarun.hotel.product').browse(cr, uid, [product_id]):
                if qty:
                    if prod.total_stock < qty:
                        warning_msg = _(
                            'Product %s has low stock. Are you sure you want to select this Product!!') % (prod.name)
                        res.update({'warning': {
                            'title': _('Warning'),
                            'message': warning_msg,
                        }
                        })
                    return res
                else:
                    res['value']['qty'] = 1.00
                    res['value']['pts_unit'] = prod.value
                    return res


tarun_hotel_purchase_lines()


class tarun_hotel_stock_stats(osv.osv):
    _name = "tarun.hotel.stock.stats"
    _description = "Stock Statistics"

    def button_gen_stats(self, cr, uid, ids, context=None):
        for do in self.browse(cr, uid, ids, context=context):
            if not (do.date_start and do.date_end):
                raise osv.except_osv(
                    _('Warning !'), _('Please specify Start and End Date to generate statistics.'))

            trans_obj = self.pool.get('tarun.hotel.stock.transfer')
            prod_obj = self.pool.get('tarun.hotel.product')
            line_obj = self.pool.get('tarun.hotel.stock.stats.lines')
            sols = line_obj.search(cr, uid, [('stats_id', '=', do.id)])
            line_obj.unlink(cr, uid, sols, context)
            prod_ids = prod_obj.search(cr, uid, [])
            t_point = 0.0
            for prod in prod_ids:
                points, serv, serv_in, serv_start = 0.0, 0.0, 0.0, 0.0
                sm_ids = trans_obj.search(
                    cr, uid, [('product_id.id', '=', prod), ('state', '=', 'done')])
                for sm in trans_obj.browse(cr, uid, sm_ids):
                    if sm.date[:10] < do.date_start:
                        if sm.loc_des_id.name == 'Stock':
                            serv_start += sm.qty
                        else:
                            serv_start -= sm.qty
                    if do.date_start <= sm.date[:10] <= do.date_end:
                        if sm.loc_des_id.name == 'Stock':
                            serv_in += sm.qty
                        else:
                            serv += sm.qty

                points += sm.qty * sm.product_id.value

                t_point += points
                line_obj.create(cr, uid, {'stats_id': do.id,
                                          'product_id': prod,
                                          'points': points,
                                          'serving': serv,
                                          'serving_start': serv_start,
                                          'serving_end': serv_start + serv_in - serv,
                                          'serving_in': serv_in,
                                          })
            name = 'Stats from %s to %s' % (do.date_start, do.date_end)
            return self.write(cr, uid, ids, {'total': t_point, 'name': name}, context=context)

    def print_csv_report(self, cr, uid, ids, context=None):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        contents = ""
        pick_ids = []
        cr.execute(
            """DELETE FROM ir_attachment WHERE res_model ='tarun.hotel.stock.stats'""")
        for wiz in self.browse(cr, uid, ids, context=context):
            fname = "Statistics from %s to %s.csv" % (
                wiz.date_start[5:], wiz.date_end[5:])
            contents += "Statistics from %s to %s \n Product,Points,Serving,Serving Start,Serving End,Serving In\n" % (
                wiz.date_start, wiz.date_end)
            for line in wiz.stat_lines:
                contents += line.product_id.name + "," + str(line.points) + "," + str(line.serving) + "," + str(
                    line.serving_start) + "," + str(line.serving_end) + "," + str(line.serving_in) + "\n"
            contents += "Total Points,%s" % (wiz.total)
            for i in ids:
                integer_id = int(i)

            data_attach = {'name': fname,
                           'datas': base64.encodestring(contents.encode('utf-8')),
                           'datas_fname': fname,
                           'res_model': self._name,
                           'description': 'description',
                           'res_id': i}
            attach_id = self.pool.get(
                'ir.attachment').create(cr, uid, data_attach)
            mod_obj = self.pool.get('ir.model.data')
            pick_ids.append(attach_id)
            action_model, action_id = tuple(
                mod_obj.get_object_reference(cr, uid, 'base', 'action_attachment'))
            action = self.pool.get(action_model).read(
                cr, uid, action_id, context=context)
            ctx = eval(action['context'])
            if pick_ids and len(pick_ids) == 1:
                form_view_ids = [
                    view_id for view_id, view in action['views'] if view == 'form']
                view_id = form_view_ids and form_view_ids[0] or False
                action.update({
                    'views': [],
                    'view_mode': 'form',
                    'view_id': view_id,
                    'res_id': pick_ids[0]
                })
            action.update({
                'context': ctx,
            })
            return action

    _columns = {
        'name': fields.char('Name', size=128, select=True),
        'date_start': fields.date('Start Date', help="Date.", required=True, select=True),
        'date_end': fields.date('End Date', help="Date.", required=True, select=True),
        'total': fields.float('Total Points'),
        'stat_lines': fields.one2many('tarun.hotel.stock.stats.lines', 'stats_id', 'Statistics Lines', readonly=True),
    }

    _defaults = {
        'date_start': lambda *a: (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'date_end': lambda *a: (datetime.now()).strftime('%Y-%m-%d'),
    }

tarun_hotel_stock_stats()


class tarun_hotel_stock_stats_lines(osv.osv):
    _name = "tarun.hotel.stock.stats.lines"
    _description = "Stock Statistics lines"

    _columns = {
        'stats_id': fields.many2one('tarun.hotel.stock.stats', 'stats'),
        'product_id': fields.many2one('tarun.hotel.product', 'Product'),
        'points': fields.float('Points'),
        'serving': fields.float('Serving', digits=(14, 3)),
        'serving_start': fields.float('Serving at Start Date', digits=(14, 3)),
        'serving_end': fields.float('Serving at End Date', digits=(14, 3)),
        'serving_in': fields.float('Serving IN', digits=(14, 3)),
    }


tarun_hotel_stock_stats_lines()
