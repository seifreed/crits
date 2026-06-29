from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from crits.core.class_mapper import class_from_type
from crits.core.mongo_tools import mongo_connector


class Command(BaseCommand):
    """
    Scan TLO collections for documents that fail to load.

    A corrupt document -- for example a relationship whose value is not a
    valid ObjectId -- makes MongoEngine raise when the document is part of a
    queryset, which breaks listings and blocks upgrades without telling you
    which document is at fault (crits#50). This command loads each document on
    its own and reports the ones that fail so they can be inspected or fixed.
    """

    help = 'Find documents that fail to load in TLO collections (crits#50).'

    def add_arguments(self, parser):
        parser.add_argument('--type', '-t', dest='type_', default=None,
                            help='Limit the scan to a single CRITs type '
                                 '(e.g. Sample). Default: all types.')

    def handle(self, *args, **options):
        type_ = options.get('type_')
        if type_ and type_ not in settings.CRITS_TYPES:
            raise CommandError("Unknown CRITs type: %s" % type_)
        types = [type_] if type_ else sorted(settings.CRITS_TYPES.keys())

        total_corrupt = 0
        for t in types:
            klass = class_from_type(t)
            if not klass:
                continue
            collection = mongo_connector(settings.CRITS_TYPES[t])
            scanned = 0
            corrupt = []
            for doc in collection.find({}, {'_id': 1}):
                scanned += 1
                try:
                    klass.objects(id=doc['_id']).first()
                except Exception as e:
                    corrupt.append((doc['_id'], str(e)))
            if corrupt:
                total_corrupt += len(corrupt)
                self.stdout.write("%s: %d corrupt of %d scanned"
                                  % (t, len(corrupt), scanned))
                for _id, err in corrupt:
                    self.stdout.write("  %s: %s" % (_id, err))
            else:
                self.stdout.write("%s: OK (%d scanned)" % (t, scanned))

        self.stdout.write("Done. %d corrupt document(s) total." % total_corrupt)
