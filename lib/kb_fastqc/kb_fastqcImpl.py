# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os,uuid
import requests,subprocess
from KBaseReport.KBaseReportClient import KBaseReport
from biokbase.workspace.client import Workspace as workspaceService
#END_HEADER


class kb_fastqc:
    '''
    Module Name:
    kb_fastqc

    Module Description:
    A KBase module: kb_fastqc
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.2"
    GIT_URL = "git@github.com:msneddon/kb_fastqc"
    GIT_COMMIT_HASH = "72a6925fa0ceccf2853b5d6743adcf31af97a7e7"

    #BEGIN_CLASS_HEADER
    
    def _get_input_file_ref_from_params(self, params):
        if 'input_file_ref' in params:
            return params['input_file_ref']
        else:
            if 'input_ws' not in params and 'input_file' not in params:
                raise ValueError('Either the "input_file_ref" field or the "input_ws" with' +
                                 '"input_file" fields must be set.')
            return str(params['input_ws']) + '/' + str(params['input_file'])

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config['workspace-url']
        self.scratch = os.path.abspath(config['scratch'])
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        #END_CONSTRUCTOR
        pass


    def runFastQC(self, ctx, input_params):
        """
        :param input_params: instance of type "FastQCParams" -> structure:
           parameter "input_ws" of String, parameter "input_file" of String,
           parameter "input_file_ref" of String
        :returns: instance of type "FastQCOutput" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: reported_output
        #BEGIN runFastQC

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        uuid_string = str(uuid.uuid4())
        read_file_path=self.scratch+"/"+uuid_string
        os.mkdir(read_file_path)

        input_file_ref = self._get_input_file_ref_from_params(input_params)

        info=None
        readLibrary=None
        try:
            readLibrary = wsClient.get_objects2({'objects': [{'ref': input_file_ref}]})['data'][0]
            info = readLibrary['info']
            readLibrary = readLibrary['data']
        except Exception as e:
            raise ValueError('Unable to get read library object from workspace: (' + input_file_ref + ')' + str(e))

        #Check type of read
        reads_type = "SE"
        if("PairedEnd" in info[2]):
            reads_type="PE"

        reads = list()
        if(reads_type == "SE"):
            if 'handle' in readLibrary:
                reads.append(readLibrary['handle'])
            elif 'lib' in readLibrary:
                reads.append(readLibrary['lib']['file'])
        elif(reads_type == "PE"):
            for number in ("1","2"):
                if 'handle_'+number in readLibrary:
                    reads.append(readLibrary['handle_'+number])
                elif 'lib'+number in readLibrary:
                    reads.append(readLibrary['lib'+number]['file'])

        read_ids = list()
        for read in reads:
            read_file_name = str(read['id'])
            if 'file_name' in read:
                read_file_name = read['file_name']
            read_ids.append(read_file_name)

        read_file_list=list()
        for read_file_name in read_ids:
            read_file_name=read_file_path+"/"+read_file_name
            read_file_list.append(read_file_name)

            read_file = open(read_file_name, 'w', 0)
            r = requests.get(read['url']+'/node/'+read['id']+'?download', stream=True, headers=headers)
            for chunk in r.iter_content(1024):
                read_file.write(chunk)


        subprocess.check_output(["fastqc"]+read_file_list)
        report = "Command run: "+" ".join(["fastqc"]+read_file_list)
        
        output_html_files = list()
        output_zip_files = list()
        html_string = ""
        for file in os.listdir(read_file_path):
            if(file.endswith(".zip")):
                output_zip_files.append({'path' : read_file_path+"/"+file, 'name' : file, 'description' : 'Zip file generated by fastqc that contains original images seen in the report'})
            if(file.endswith(".html")):
                output_html_files.append({'path' : read_file_path+"/"+file, 'name' : file, 'description' : 'HTML file generated by fastqc that contains report on quality of reads'})
                if(html_string == ""):
                    html_file = open(read_file_path+"/"+file, 'r')
                    html_string += html_file.read()

#        html_string = "<html><title>FastQC Report</title><body>"
#        html_string += "<p>FastQC run with "+str(input_params["input_file"])+" which contained "+str(len(reads))+" reads:</p>"
#        for read in read_ids:
#            html_string += read+"<br/>"
#        html_string += "</html>"
        report_params = { 'message' : report, 'objects_created' : [],
                          'direct_html' : html_string,
                          'file_links' : output_zip_files, 
                          'html_links' : output_html_files,
                          'direct_html_index' : 0,
                          'workspace_name' : input_params['input_ws'],
                          'report_object_name' : 'kb_fastqc_report_' + uuid_string }
        kbase_report_client = KBaseReport(self.callback_url, token=token)
        output = kbase_report_client.create_extended_report(report_params)
        reported_output = { 'report_name': output['name'], 'report_ref': output['ref'] }

        #END runFastQC

        # At some point might do deeper type checking...
        if not isinstance(reported_output, dict):
            raise ValueError('Method runFastQC return value ' +
                             'reported_output is not type dict as required.')
        # return the results
        return [reported_output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK", 'message': "", 'version': self.VERSION, 
                     'git_url': self.GIT_URL, 'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
